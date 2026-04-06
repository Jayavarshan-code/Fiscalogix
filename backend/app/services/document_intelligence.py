"""
Document Intelligence Agent (DIA) — Layer 3 of the Fiscalogix Intelligence Stack.

Pipeline per document:
  1. OCR / Text extraction  — pdfplumber for PDFs, UTF-8 decode for text files
  2. LLM classification     — determines doc type (CONTRACT, INVOICE, PERMIT, BOL)
  3. Specialist extraction  — per-type LLM prompt returns structured JSON
  4. Guardrail validation   — rejects hallucinated financial values
  5. DB write-back          — extracted penalty rate → Shipment.nlp_extracted_penalty_rate
  6. RAG ingestion          — embeds extracted fields into knowledge base for future retrieval

Design contract:
- The LLM never touches raw financial calculations.
  It only extracts text values that already exist in the document.
- All extracted numeric fields go through _apply_guardrails() before any DB write.
- If the LLM is offline, the pipeline degrades gracefully:
  classification falls back to filename heuristics,
  extraction falls back to regex patterns.
"""

import io
import re
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple

from app.models.document_intelligence import (
    ExtractedDocument, DocumentType, ValidationStatus,
)
from app.services.llm_gateway import LlmGateway

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# GUARDRAIL CONSTANTS  (hard limits — if LLM returns outside these, reject)
# ─────────────────────────────────────────────────────────────────────────────
MAX_PENALTY_RATE_PCT   = 0.50   # 50% / day is physically impossible in any contract
MAX_PENALTY_CAP_PCT    = 1.00   # Penalty can never exceed 100% of order value
MAX_PAYMENT_TERMS_DAYS = 365    # Net-365 is the longest real-world credit term
MIN_CONFIDENCE_FOR_DB  = 0.70   # Below this, flag for human review; don't write to DB


class DocumentIntelligenceService:
    """
    Layer 3: Document Intelligence Agent.

    Processes uploaded logistics documents and extracts structured financial
    data (penalty rates, payment terms, Incoterms, permit expiry dates) that
    feeds directly into the ReVM calculation engine.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.llm = LlmGateway(api_key=api_key)

    # ─────────────────────────────────────────────────────────────────────────
    # PUBLIC ENTRY POINT
    # ─────────────────────────────────────────────────────────────────────────

    async def process_document(
        self,
        file_content: bytes,
        filename: str,
        shipment_id: Optional[int] = None,
        tenant_id: str = "default_tenant",
    ) -> ExtractedDocument:
        """
        Full DIA pipeline: extract → classify → parse → validate → persist.

        Args:
            file_content: Raw bytes of the uploaded file.
            filename:     Original filename (used for fallback classification).
            shipment_id:  If provided, writes extracted penalty rate back to the
                          Shipment row and triggers ReVM recalculation.
            tenant_id:    Used for RAG ingestion scoping.
        """
        doc_id = f"doc_{int(datetime.utcnow().timestamp())}"

        # Step 1: Extract raw text
        raw_text, extraction_method = self._extract_text(file_content, filename)
        logger.info(f"DIA [{doc_id}]: text extracted via {extraction_method} ({len(raw_text)} chars)")

        # Step 2: Classify document type
        doc_type = await self._classify(raw_text, filename)
        logger.info(f"DIA [{doc_id}]: classified as {doc_type}")

        # Step 3: Specialist extraction
        structured_data, confidence = await self._extract_structured(raw_text, doc_type)

        # Step 4: Guardrail validation
        structured_data, validation_status = self._apply_guardrails(structured_data, doc_type)

        # Step 5: Write-back to DB (only if confidence is high enough)
        if shipment_id and confidence >= MIN_CONFIDENCE_FOR_DB:
            self._writeback_to_shipment(structured_data, doc_type, shipment_id)

        # Step 6: Embed into RAG knowledge base
        self._ingest_to_rag(structured_data, doc_type, doc_id, tenant_id)

        return ExtractedDocument(
            doc_id=doc_id,
            doc_type=doc_type,
            confidence_score=confidence,
            raw_text=raw_text[:2000],   # truncate for storage — full text not needed
            structured_data={
                **structured_data,
                "validation": {
                    "status": validation_status,
                    "confidence": confidence,
                    "extraction_method": extraction_method,
                    "verified_at": datetime.utcnow().isoformat(),
                },
            },
            metadata={
                "filename": filename,
                "shipment_id": shipment_id,
                "tenant_id": tenant_id,
                "char_count": len(raw_text),
            },
        )

    # ─────────────────────────────────────────────────────────────────────────
    # STEP 1: TEXT EXTRACTION
    # ─────────────────────────────────────────────────────────────────────────

    def _extract_text(self, content: bytes, filename: str) -> Tuple[str, str]:
        """
        Returns (text, method_used).
        Tries pdfplumber for PDFs, UTF-8 decode for everything else.
        """
        fn_lower = filename.lower()

        if fn_lower.endswith(".pdf"):
            text = self._extract_pdf(content)
            if text.strip():
                return text, "pdfplumber"
            # PDF was image-only (scanned) — fall back to filename heuristics
            logger.warning(f"DIA: PDF '{filename}' yielded no text — likely scanned. OCR not available.")
            return f"[Scanned PDF: {filename}]", "scan_fallback"

        # Plain text / CSV / XML
        for encoding in ("utf-8", "latin-1", "cp1252"):
            try:
                return content.decode(encoding), f"text_{encoding}"
            except UnicodeDecodeError:
                continue

        return content.decode("utf-8", errors="replace"), "text_lossy"

    def _extract_pdf(self, content: bytes) -> str:
        """Uses pdfplumber to extract text from all pages."""
        try:
            import pdfplumber
            with pdfplumber.open(io.BytesIO(content)) as pdf:
                pages = []
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        pages.append(page_text)
                return "\n\n".join(pages)
        except Exception as e:
            logger.error(f"DIA._extract_pdf: pdfplumber failed — {e}")
            return ""

    # ─────────────────────────────────────────────────────────────────────────
    # STEP 2: CLASSIFICATION
    # ─────────────────────────────────────────────────────────────────────────

    async def _classify(self, text: str, filename: str) -> DocumentType:
        """
        Primary: LLM classification (temperature=0, deterministic).
        Fallback: keyword heuristic on text + filename.
        """
        llm_type = await self.llm.classify_document(text, filename)

        type_map = {
            "CONTRACT":       DocumentType.CONTRACT,
            "INVOICE":        DocumentType.INVOICE,
            "PERMIT":         DocumentType.PERMIT,
            "BILL_OF_LADING": DocumentType.BILL_OF_LADING,
        }
        if llm_type in type_map:
            return type_map[llm_type]

        # Fallback: keyword heuristic
        return self._classify_heuristic(text, filename)

    def _classify_heuristic(self, text: str, filename: str) -> DocumentType:
        """Keyword-based fallback when LLM is offline."""
        combined = (text[:500] + filename).lower()
        if any(k in combined for k in ("agreement", "contract", "msa", "sla", "terms")):
            return DocumentType.CONTRACT
        if any(k in combined for k in ("invoice", "inv-", "bill to", "amount due")):
            return DocumentType.INVOICE
        if any(k in combined for k in ("permit", "license", "hazmat", "authority")):
            return DocumentType.PERMIT
        if any(k in combined for k in ("bill of lading", "bol", "shipper", "consignee", "bl number")):
            return DocumentType.BILL_OF_LADING
        return DocumentType.BILL_OF_LADING   # safest default for logistics docs

    # ─────────────────────────────────────────────────────────────────────────
    # STEP 3: SPECIALIST EXTRACTION
    # ─────────────────────────────────────────────────────────────────────────

    async def _extract_structured(
        self, text: str, doc_type: DocumentType
    ) -> Tuple[Dict[str, Any], float]:
        """
        Routes to the appropriate specialist extractor.
        Returns (structured_data, confidence_score).
        """
        if doc_type == DocumentType.CONTRACT:
            return await self._extract_contract(text)
        if doc_type == DocumentType.INVOICE:
            return await self._extract_invoice(text)
        if doc_type == DocumentType.PERMIT:
            return await self._extract_permit(text)
        if doc_type == DocumentType.BILL_OF_LADING:
            return await self._extract_bol(text)
        # Fallback for other types
        return {"raw_text_preview": text[:500]}, 0.60

    async def _extract_contract(self, text: str) -> Tuple[Dict[str, Any], float]:
        """
        Extracts financial terms from SLA/MSA contracts.
        These fields directly feed the ReVM formula:
          - penalty_rate_per_day_pct → SLAModel.compute()
          - payment_terms_days        → TimeValueModel.compute()
          - incoterms                 → risk transfer point for FX/risk models
        """
        # Primary: LLM extraction
        extracted = await self.llm.extract_document_fields(text, "CONTRACT")

        if extracted:
            confidence = self._score_extraction_confidence(extracted, [
                "penalty_rate_per_day_pct", "payment_terms_days", "incoterms"
            ])
            return extracted, confidence

        # Fallback: regex patterns for common contract formats
        logger.info("DIA: LLM extraction empty — using regex fallback for CONTRACT")
        return self._regex_extract_contract(text), 0.55

    async def _extract_invoice(self, text: str) -> Tuple[Dict[str, Any], float]:
        """Extracts invoice amounts and line items for BoL reconciliation."""
        extracted = await self.llm.extract_document_fields(text, "INVOICE")
        if extracted:
            confidence = self._score_extraction_confidence(extracted, [
                "invoice_number", "total_amount_usd", "payment_due_date"
            ])
            return extracted, confidence
        return self._regex_extract_invoice(text), 0.50

    async def _extract_permit(self, text: str) -> Tuple[Dict[str, Any], float]:
        """Extracts permit/license validity and scope."""
        extracted = await self.llm.extract_document_fields(text, "PERMIT")
        if extracted:
            confidence = self._score_extraction_confidence(extracted, [
                "permit_number", "expiry_date", "issuing_authority"
            ])
            return extracted, confidence
        return self._regex_extract_permit(text), 0.55

    async def _extract_bol(self, text: str) -> Tuple[Dict[str, Any], float]:
        """Extracts shipment identifiers and routing from Bill of Lading."""
        extracted = await self.llm.extract_document_fields(text, "BILL_OF_LADING")
        if extracted:
            confidence = self._score_extraction_confidence(extracted, [
                "bol_number", "shipper", "consignee", "port_of_discharge"
            ])
            return extracted, confidence
        return self._regex_extract_bol(text), 0.50

    # ─────────────────────────────────────────────────────────────────────────
    # REGEX FALLBACKS (when LLM is offline)
    # ─────────────────────────────────────────────────────────────────────────

    def _regex_extract_contract(self, text: str) -> Dict[str, Any]:
        """Regex patterns for common SLA/MSA contract formats."""
        result: Dict[str, Any] = {}

        # Penalty rate: "5% per day", "2.5% per 24 hours", "$500/day"
        pct_match = re.search(
            r"(\d+(?:\.\d+)?)\s*%\s*(?:per|/)\s*(?:day|24\s*h)", text, re.IGNORECASE
        )
        if pct_match:
            result["penalty_rate_per_day_pct"] = float(pct_match.group(1)) / 100

        # Penalty cap: "not to exceed 15%", "maximum penalty: 20%"
        cap_match = re.search(
            r"(?:not to exceed|maximum penalty[:\s]+|capped at)\s*(\d+(?:\.\d+)?)\s*%",
            text, re.IGNORECASE
        )
        if cap_match:
            result["penalty_cap_pct"] = float(cap_match.group(1)) / 100

        # Payment terms: "Net-30", "Net 60", "payment within 45 days"
        net_match = re.search(
            r"(?:net[-\s]?(\d+)|payment\s+(?:within|terms?)[:\s]+(\d+)\s*days?)",
            text, re.IGNORECASE
        )
        if net_match:
            days = net_match.group(1) or net_match.group(2)
            result["payment_terms_days"] = int(days)

        # Incoterms: CIF, FOB, DDP, EXW, DAP, etc.
        inco_match = re.search(
            r"\b(EXW|FCA|CPT|CIP|DAP|DPU|DDP|FAS|FOB|CFR|CIF)\b", text
        )
        if inco_match:
            result["incoterms"] = inco_match.group(1)

        # Force majeure
        result["force_majeure_clause"] = bool(
            re.search(r"force\s+majeure", text, re.IGNORECASE)
        )

        return result

    def _regex_extract_invoice(self, text: str) -> Dict[str, Any]:
        result: Dict[str, Any] = {}
        inv_match = re.search(r"(?:invoice|inv)[#\s:\-]+([A-Z0-9\-]+)", text, re.IGNORECASE)
        if inv_match:
            result["invoice_number"] = inv_match.group(1)
        amt_match = re.search(r"(?:total|amount due|grand total)[:\s\$]+([0-9,]+(?:\.\d{2})?)", text, re.IGNORECASE)
        if amt_match:
            result["total_amount_usd"] = float(amt_match.group(1).replace(",", ""))
        return result

    def _regex_extract_permit(self, text: str) -> Dict[str, Any]:
        result: Dict[str, Any] = {}
        permit_match = re.search(r"permit\s*[#no\.:\s]+([A-Z0-9\-]+)", text, re.IGNORECASE)
        if permit_match:
            result["permit_number"] = permit_match.group(1)
        date_match = re.search(r"expir(?:y|es?|ation)[:\s]+(\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4})", text, re.IGNORECASE)
        if date_match:
            result["expiry_date"] = date_match.group(1)
        return result

    def _regex_extract_bol(self, text: str) -> Dict[str, Any]:
        result: Dict[str, Any] = {}
        bol_match = re.search(r"b/?l\s*(?:no\.?|number|#)[:\s]+([A-Z0-9\-]+)", text, re.IGNORECASE)
        if bol_match:
            result["bol_number"] = bol_match.group(1)
        return result

    # ─────────────────────────────────────────────────────────────────────────
    # STEP 4: GUARDRAIL VALIDATION
    # ─────────────────────────────────────────────────────────────────────────

    def _apply_guardrails(
        self, data: Dict[str, Any], doc_type: DocumentType
    ) -> Tuple[Dict[str, Any], str]:
        """
        Validates extracted values against physical constraints.
        Returns (sanitized_data, validation_status).

        Rejects hallucinated values that would corrupt the ReVM formula:
        - penalty_rate_per_day_pct > 50%  → impossible in any real contract
        - penalty_cap_pct > 100%           → logically impossible
        - payment_terms_days > 365         → no real business grants Net-366
        """
        issues = []

        if doc_type == DocumentType.CONTRACT:
            rate = data.get("penalty_rate_per_day_pct")
            if rate is not None:
                if not isinstance(rate, (int, float)) or rate < 0:
                    issues.append(f"penalty_rate_per_day_pct invalid: {rate}")
                    data["penalty_rate_per_day_pct"] = None
                elif rate > MAX_PENALTY_RATE_PCT:
                    issues.append(f"penalty_rate_per_day_pct {rate:.1%} exceeds max {MAX_PENALTY_RATE_PCT:.0%}")
                    data["penalty_rate_per_day_pct"] = None

            cap = data.get("penalty_cap_pct")
            if cap is not None and cap > MAX_PENALTY_CAP_PCT:
                issues.append(f"penalty_cap_pct {cap:.1%} exceeds 100%")
                data["penalty_cap_pct"] = None

            terms = data.get("payment_terms_days")
            if terms is not None and terms > MAX_PAYMENT_TERMS_DAYS:
                issues.append(f"payment_terms_days {terms} > {MAX_PAYMENT_TERMS_DAYS}")
                data["payment_terms_days"] = None

        if doc_type == DocumentType.INVOICE:
            amount = data.get("total_amount_usd")
            if amount is not None and (amount < 0 or amount > 1_000_000_000):
                issues.append(f"total_amount_usd {amount} out of plausible range")
                data["total_amount_usd"] = None

        if issues:
            logger.warning(f"DIA guardrails triggered: {issues}")
            return data, ValidationStatus.PENDING_REVIEW

        return data, ValidationStatus.VERIFIED

    # ─────────────────────────────────────────────────────────────────────────
    # STEP 5: DB WRITE-BACK
    # ─────────────────────────────────────────────────────────────────────────

    def _writeback_to_shipment(
        self,
        data: Dict[str, Any],
        doc_type: DocumentType,
        shipment_id: int,
    ):
        """
        Writes extracted contract terms back to the Shipment row.
        This closes the loop: uploaded SLA → nlp_extracted_penalty_rate
        populated → SLAModel.compute() uses real contract rate instead of default.
        """
        if doc_type != DocumentType.CONTRACT:
            return

        penalty_rate = data.get("penalty_rate_per_day_pct")
        if penalty_rate is None:
            return

        try:
            from app.Db.connections import SessionLocal
            from setup_db import Shipment

            db = SessionLocal()
            try:
                shipment = db.query(Shipment).filter(
                    Shipment.shipment_id == shipment_id
                ).first()
                if shipment:
                    shipment.nlp_extracted_penalty_rate = penalty_rate
                    # Also write payment terms if extracted
                    if data.get("payment_terms_days") and hasattr(shipment, "credit_days"):
                        # Don't overwrite manual credit_days — only write if currently null
                        if shipment.total_cost is None:
                            pass  # future: write credit_days to customer record
                    db.commit()
                    logger.info(
                        f"DIA: wrote penalty_rate={penalty_rate:.3f} to shipment {shipment_id}"
                    )
            finally:
                db.close()

        except Exception as e:
            logger.error(f"DIA._writeback_to_shipment: {e}")

    # ─────────────────────────────────────────────────────────────────────────
    # STEP 6: RAG INGESTION
    # ─────────────────────────────────────────────────────────────────────────

    def _ingest_to_rag(
        self,
        data: Dict[str, Any],
        doc_type: DocumentType,
        doc_id: str,
        tenant_id: str,
    ):
        """
        Embeds extracted document fields into the RAG knowledge base.
        Future LLM calls can retrieve this as grounding context.
        """
        try:
            from app.services.rag.ingestion import RAGIngestionPipeline
            source_type_map = {
                DocumentType.CONTRACT:       "sla_contract",
                DocumentType.PERMIT:         "permit",
                DocumentType.INVOICE:        "invoice",
                DocumentType.BILL_OF_LADING: "bill_of_lading",
            }
            RAGIngestionPipeline().ingest_document(
                extracted_data=data,
                tenant_id=tenant_id,
                source_type=source_type_map.get(doc_type, "document"),
                source_id=doc_id,
            )
        except Exception as e:
            logger.warning(f"DIA: RAG ingestion skipped — {e}")

    # ─────────────────────────────────────────────────────────────────────────
    # CROSS-DOCUMENT ANALYSIS
    # ─────────────────────────────────────────────────────────────────────────

    def detect_semantic_gaps(
        self,
        contract: ExtractedDocument,
        insurance: ExtractedDocument,
    ) -> List[str]:
        """
        Identifies coverage gaps between a contract and insurance policy.
        E.g.: contract liability limit > insurance coverage limit.
        """
        gaps = []
        contract_limit  = contract.structured_data.get("liability_limit_usd", 0) or 0
        insurance_limit = insurance.structured_data.get("coverage_limit_usd", 0) or 0

        if contract_limit > 0 and insurance_limit > 0:
            if contract_limit > insurance_limit:
                gap = contract_limit - insurance_limit
                gaps.append(
                    f"LIABILITY GAP: Contract requires ${contract_limit:,.0f} coverage "
                    f"but insurance only covers ${insurance_limit:,.0f}. "
                    f"Uncovered exposure: ${gap:,.0f}."
                )

        # Check Incoterms vs insurance scope
        incoterms = contract.structured_data.get("incoterms")
        insurance_scope = insurance.structured_data.get("coverage_scope", [])
        if incoterms == "FOB" and "port_to_port" not in str(insurance_scope).lower():
            gaps.append(
                "INCOTERMS MISMATCH: Contract uses FOB (buyer's risk from port of loading) "
                "but insurance scope does not explicitly cover port-to-port transit."
            )

        return gaps

    def generate_autonomous_dispute(
        self,
        invoice: ExtractedDocument,
        contract: ExtractedDocument,
    ) -> Optional[Dict[str, Any]]:
        """
        Compares an invoice amount against the contract's agreed rate.
        Returns a dispute record if a billing variance is detected.
        """
        inv_amount   = invoice.structured_data.get("total_amount_usd")
        agreed_rate  = contract.structured_data.get("agreed_rate_usd")

        if not inv_amount or not agreed_rate:
            return None

        variance_pct = abs(inv_amount - agreed_rate) / max(agreed_rate, 1)
        if variance_pct < 0.01:   # < 1% variance — within tolerance
            return None

        return {
            "dispute_type":    "BILLING_VARIANCE",
            "invoice_id":      invoice.doc_id,
            "contract_id":     contract.doc_id,
            "invoiced_amount": inv_amount,
            "agreed_amount":   agreed_rate,
            "variance_pct":    round(variance_pct * 100, 2),
            "action":          "DISPUTE" if variance_pct > 0.05 else "QUERY",
            "generated_at":    datetime.utcnow().isoformat(),
        }

    def trigger_alerts(self, doc: ExtractedDocument) -> List[str]:
        """
        Scans an extracted document for time-sensitive alerts.
        Called by the /documents/alerts/all endpoint.
        """
        alerts = []
        data = doc.structured_data

        # Permit expiry warning (30-day window)
        expiry_str = data.get("expiry_date")
        if expiry_str:
            try:
                for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y"):
                    try:
                        expiry = datetime.strptime(expiry_str, fmt)
                        days_left = (expiry - datetime.utcnow()).days
                        if days_left < 0:
                            alerts.append(
                                f"EXPIRED: Document {doc.doc_id} ({doc.doc_type}) "
                                f"expired {abs(days_left)} days ago."
                            )
                        elif days_left <= 30:
                            alerts.append(
                                f"EXPIRY WARNING: Document {doc.doc_id} ({doc.doc_type}) "
                                f"expires in {days_left} days."
                            )
                        break
                    except ValueError:
                        continue
            except Exception:
                pass

        # High penalty rate alert
        rate = data.get("penalty_rate_per_day_pct")
        if rate and rate > 0.05:
            alerts.append(
                f"HIGH PENALTY RATE: Contract {doc.doc_id} carries "
                f"{rate * 100:.1f}%/day — exceeds the 5% risk threshold."
            )

        # Missing force majeure
        if doc.doc_type == DocumentType.CONTRACT:
            if data.get("force_majeure_clause") is False:
                alerts.append(
                    f"MISSING CLAUSE: Contract {doc.doc_id} has no force majeure clause. "
                    "Review before signing in geopolitically volatile corridors."
                )

        return alerts

    # ─────────────────────────────────────────────────────────────────────────
    # HELPERS
    # ─────────────────────────────────────────────────────────────────────────

    def _score_extraction_confidence(
        self, data: Dict[str, Any], required_fields: List[str]
    ) -> float:
        """
        Scores extraction quality by how many required fields were populated.
        0.99 → all fields present
        0.70 → half present
        0.50 → none present (LLM returned empty/null for everything)
        """
        if not data:
            return 0.50
        found = sum(1 for f in required_fields if data.get(f) is not None)
        base = found / max(len(required_fields), 1)
        # Scale to 0.50–0.99 range
        return round(0.50 + base * 0.49, 2)
