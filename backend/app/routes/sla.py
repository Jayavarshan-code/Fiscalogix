"""
SLA Contract Analysis Pipeline — /sla

Full end-to-end pipeline in one module:

  Stage 1  Parse        PDF bytes → pdfplumber → raw text
  Stage 2  Extract      SLAContractExtractor regex (+ LLM fallback) → clauses
  Stage 3  Calculate    SLAPenaltyModel.compute_with_detail() → penalty breakdown
  Stage 4  Score        Severity distribution → composite risk score (0–100)
  Stage 5  Output       Structured SLAAnalysisResult response

Routes
------
  POST /sla/parse          Upload PDF → full clause extraction only
  POST /sla/analyze        Upload PDF + shipment context → complete analysis
  POST /sla/text           Raw text input (no file) → clause extraction
  POST /sla/negotiate      Supplier data → LLM negotiation strategy
"""

import csv
import io
import logging
from typing import Any, Dict, List, Optional

import pdfplumber
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from pydantic import BaseModel, Field

from app.financial_system.dependencies import get_current_user
from app.financial_system.sla_model import SLAPenaltyModel
from app.ml.sla_extractor import SLAContractExtractor

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/sla", tags=["SLA Contract Pipeline"])

_penalty_model = SLAPenaltyModel()

# ── Constants ─────────────────────────────────────────────────────────────────
MAX_PDF_BYTES = 20 * 1024 * 1024   # 20 MB
_SEVERITY_WEIGHTS = {"CRITICAL": 25, "HIGH": 10, "MEDIUM": 4, "LOW": 1, "NONE": 0}


# ── Request / Response schemas ────────────────────────────────────────────────

class ShipmentContext(BaseModel):
    """Optional shipment row data used to calculate the actual penalty amount."""
    order_value:                  float = Field(0.0,       description="Order / contract value in USD")
    contract_type:                str   = Field("standard", description="full_rejection | strict | standard | lenient")
    customer_tier:                str   = Field("standard", description="enterprise | strategic | growth | standard | spot | trial")
    predicted_delay_days:         float = Field(0.0,       description="Number of days delayed (0 = no delay)")
    otif_actual_pct:              Optional[float] = Field(None, description="Actual OTIF % — drives breach multiplier")
    otif_threshold_pct:           float = Field(95.0,      description="Contracted OTIF threshold")
    nlp_extracted_penalty_rate:   Optional[float] = None   # auto-populated from extraction


class SLAParseResponse(BaseModel):
    total_clauses:          int
    critical_count:         int
    high_risk_count:        int
    overall_confidence:     str
    penalty_rate:           Optional[float]
    flat_fee_per_day:       Optional[float]
    force_majeure_applies:  bool
    cap_limit:              Optional[float]
    clauses:                List[Dict[str, Any]]
    bottleneck_clauses:     List[Dict[str, Any]]
    llm_assisted:           bool
    llm_analysis:           Optional[Dict[str, Any]] = None


class SLAAnalysisResult(BaseModel):
    contract_text_preview:  str
    extraction:             SLAParseResponse
    penalty:                Optional[Dict[str, Any]]
    risk_score:             int              # 0–100 composite severity score
    severity_distribution:  Dict[str, int]  # CRITICAL/HIGH/MEDIUM/LOW counts
    top_bottlenecks:        List[Dict[str, Any]]
    processing_pipeline:    List[str]


class SLATextRequest(BaseModel):
    text:       str   = Field(..., min_length=20, description="Raw contract text")
    use_llm:    bool  = Field(False,  description="Force LLM-assisted extraction even if regex succeeds")
    tenant_id:  str   = Field("default_tenant")


class SLANegotiateRequest(BaseModel):
    supplier_data:    Dict[str, Any]
    contract_clauses: Optional[List[Dict[str, Any]]] = None
    tenant_id:        str = "default_tenant"


# ── Internal helpers ─────────────────────────────────────────────────────────

def _pdf_to_text(content: bytes, filename: str) -> str:
    """Extract plain text from a PDF using pdfplumber."""
    if len(content) > MAX_PDF_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"PDF '{filename}' exceeds the 20 MB limit.",
        )
    try:
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            pages = [page.extract_text() or "" for page in pdf.pages]
        text = "\n".join(pages).strip()
        if not text:
            raise HTTPException(status_code=422, detail="PDF appears to be image-only or empty — no text extracted.")
        return text
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"PDF parsing failed: {e}") from e


def _score_extraction(extraction: Dict[str, Any]) -> tuple[int, Dict[str, int], List[Dict[str, Any]]]:
    """
    Compute a composite risk score (0–100), severity distribution, and top 5 bottlenecks.

    Score is the sum of severity weights across all bottleneck clauses, clamped to 100.
    CRITICAL clause = +25 pts, HIGH = +10, MEDIUM = +4, LOW = +1.
    """
    dist: Dict[str, int] = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0, "NONE": 0}
    raw_score = 0

    for clause in extraction.get("clauses", []):
        sev = clause.get("bottleneck_severity", "NONE")
        dist[sev] = dist.get(sev, 0) + 1
        raw_score += _SEVERITY_WEIGHTS.get(sev, 0)

    risk_score = min(100, raw_score)

    top_bottlenecks = sorted(
        extraction.get("bottleneck_clauses", []),
        key=lambda c: _SEVERITY_WEIGHTS.get(c.get("bottleneck_severity", "NONE"), 0),
        reverse=True,
    )[:5]

    return risk_score, dist, top_bottlenecks


def _to_parse_response(extraction: Dict[str, Any]) -> "SLAParseResponse":
    """Map extractor dict keys → SLAParseResponse (handles total_clauses_found rename)."""
    return SLAParseResponse(
        total_clauses=extraction.get("total_clauses_found", 0),
        critical_count=extraction.get("critical_count", 0),
        high_risk_count=extraction.get("high_risk_count", 0),
        overall_confidence=extraction.get("overall_confidence", "LOW"),
        penalty_rate=extraction.get("penalty_rate"),
        flat_fee_per_day=extraction.get("flat_fee_per_day"),
        force_majeure_applies=extraction.get("force_majeure_applies", False),
        cap_limit=extraction.get("cap_limit"),
        clauses=extraction.get("clauses", []),
        bottleneck_clauses=extraction.get("bottleneck_clauses", []),
        llm_assisted=extraction.get("llm_assisted", False),
        llm_analysis=extraction.get("llm_analysis"),
    )


def _run_penalty(extraction: Dict[str, Any], ctx: ShipmentContext) -> Optional[Dict[str, Any]]:
    """Run SLAPenaltyModel with the NLP-extracted rate if found, else fallback to tier heuristic."""
    if ctx.predicted_delay_days <= 0:
        return None

    row = ctx.model_dump()
    # Override penalty rate with NLP-extracted value if regex found one
    if extraction.get("penalty_rate") is not None:
        row["nlp_extracted_penalty_rate"] = extraction["penalty_rate"]
    if extraction.get("cap_limit") is not None:
        row["nlp_extracted_penalty_cap"] = extraction["cap_limit"]

    return _penalty_model.compute_with_detail(row, ctx.predicted_delay_days)


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("/parse", response_model=SLAParseResponse, summary="Stage 1+2: Parse PDF → extract clauses")
async def parse_contract(
    file: UploadFile = File(..., description="Contract PDF"),
    use_llm: bool = Query(False, description="Force LLM-assisted extraction even when regex succeeds"),
    tenant_id: str = Query("default_tenant"),
    _user: dict = Depends(get_current_user),
):
    """
    Upload a contract PDF. Returns all extracted clauses, bottleneck flags,
    penalty rates, force-majeure triggers, and confidence scores.

    Regex extraction completes in <50 ms for any contract size.
    LLM fallback is auto-triggered when regex finds nothing or >50% LOW confidence;
    pass use_llm=true to force it regardless.
    """
    content = await file.read()
    raw_text = _pdf_to_text(content, file.filename)

    pipeline: List[str] = ["pdf_parse", "regex_extract"]

    if use_llm:
        extraction = await SLAContractExtractor.extract_with_llm(raw_text, tenant_id)
        if extraction.get("llm_assisted"):
            pipeline.append("llm_fallback")
    else:
        extraction = SLAContractExtractor.extract(raw_text)

    return _to_parse_response(extraction)


@router.post("/text", response_model=SLAParseResponse, summary="Stage 2 only: Extract clauses from raw text")
async def parse_text(
    body: SLATextRequest,
    _user: dict = Depends(get_current_user),
):
    """
    Submit raw contract text (no file upload). Useful for testing, webhooks,
    or when text was already extracted upstream.
    """
    if body.use_llm:
        extraction = await SLAContractExtractor.extract_with_llm(body.text, body.tenant_id)
    else:
        extraction = SLAContractExtractor.extract(body.text)

    return _to_parse_response(extraction)


@router.post(
    "/analyze",
    response_model=SLAAnalysisResult,
    summary="Full pipeline: Parse → Extract → Penalty → Score → Output",
)
async def analyze_contract(
    file: UploadFile = File(..., description="Contract PDF"),
    order_value:           float         = Query(0.0),
    contract_type:         str           = Query("standard"),
    customer_tier:         str           = Query("standard"),
    predicted_delay_days:  float         = Query(0.0),
    otif_actual_pct:       Optional[float] = Query(None),
    otif_threshold_pct:    float         = Query(95.0),
    use_llm:               bool          = Query(False),
    tenant_id:             str           = Query("default_tenant"),
    _user: dict = Depends(get_current_user),
):
    """
    The complete SLA analysis pipeline in a single call:

    1. **Parse**    — PDF → text via pdfplumber
    2. **Extract**  — 20-pattern regex extraction (+ optional LLM fallback)
    3. **Calculate** — Penalty amount using extracted rate + OTIF breach multiplier
    4. **Score**    — Composite risk score (0–100) from severity-weighted clause count
    5. **Output**   — Structured result with clauses, penalty breakdown, top bottlenecks

    Pass `predicted_delay_days > 0` and `order_value > 0` to get a concrete penalty amount.
    """
    ctx = ShipmentContext(
        order_value=order_value,
        contract_type=contract_type,
        customer_tier=customer_tier,
        predicted_delay_days=predicted_delay_days,
        otif_actual_pct=otif_actual_pct,
        otif_threshold_pct=otif_threshold_pct,
    )

    pipeline: List[str] = []

    # Stage 1 — Parse
    pipeline.append("pdf_parse")
    content  = await file.read()
    raw_text = _pdf_to_text(content, file.filename)

    # Stage 2 — Extract
    pipeline.append("regex_extract")
    if use_llm:
        extraction = await SLAContractExtractor.extract_with_llm(raw_text, tenant_id)
        if extraction.get("llm_assisted"):
            pipeline.append("llm_fallback")
    else:
        extraction = SLAContractExtractor.extract(raw_text)

    # Stage 3 — Calculate penalty
    pipeline.append("penalty_calc")
    penalty = _run_penalty(extraction, ctx)

    # Stage 4 — Score
    pipeline.append("severity_scoring")
    risk_score, sev_dist, top_bottlenecks = _score_extraction(extraction)

    # Stage 5 — Build response
    pipeline.append("output")
    parse_resp = _to_parse_response(extraction)

    return SLAAnalysisResult(
        contract_text_preview=raw_text[:400],
        extraction=parse_resp,
        penalty=penalty,
        risk_score=risk_score,
        severity_distribution=sev_dist,
        top_bottlenecks=top_bottlenecks,
        processing_pipeline=pipeline,
    )


# ── Column name aliases (CSV header normalisation) ────────────────────────────
_COL_ALIASES: Dict[str, List[str]] = {
    "shipment_id":   ["shipment_id", "id", "order_id", "shipment_no", "shipment_number", "ref"],
    "order_value":   ["order_value", "value", "amount", "invoice_value", "shipment_value", "contract_value"],
    "delay_days":    ["delay_days", "delay", "days_delayed", "actual_delay", "late_days", "delay_count"],
    "otif_actual":   ["otif_actual", "otif", "otif_pct", "otif_percent", "on_time_pct", "delivery_pct"],
    "contract_type": ["contract_type", "sla_type", "contract", "sla_tier"],
    "customer_tier": ["customer_tier", "tier", "account_tier", "client_tier"],
    "in_full_pct":   ["in_full_pct", "in_full", "fill_rate", "fill_pct", "quantity_pct"],
    "route":         ["route", "lane", "origin_destination", "od_pair"],
    "carrier":       ["carrier", "forwarder", "carrier_name", "vendor"],
}

def _resolve_col(header: str) -> Optional[str]:
    """Return canonical field name for a CSV column header, or None if unknown."""
    h = header.strip().lower().replace(" ", "_").replace("-", "_")
    for canonical, aliases in _COL_ALIASES.items():
        if h in aliases:
            return canonical
    return None


def _safe_float(val: str, default: float = 0.0) -> float:
    try:
        return float(val.strip().replace(",", "").replace("%", ""))
    except (ValueError, AttributeError):
        return default


def _breach_level(delay: float, otif: Optional[float], threshold: float) -> str:
    otif_breach = otif is not None and otif < threshold
    if delay > 14 or (otif_breach and otif is not None and otif < 82):
        return "CRITICAL"
    if delay > 7 or (otif_breach and otif is not None and otif < 88):
        return "HIGH"
    if delay > 3 or (otif_breach and otif is not None and otif < 92):
        return "MEDIUM"
    if delay > 0 or otif_breach:
        return "LOW"
    return "NONE"


@router.post("/analyze-csv", summary="Interpret shipment CSV against SLA terms")
async def analyze_csv(
    file: UploadFile = File(..., description="CSV file with shipment rows"),
    penalty_rate:     Optional[float] = Query(None,  description="Override penalty rate (fraction/day, e.g. 0.005)"),
    otif_threshold:   float           = Query(94.5,  description="Contracted OTIF threshold %"),
    contract_type:    str             = Query("standard"),
    customer_tier:    str             = Query("standard"),
    default_order_value: float        = Query(0.0,   description="Used for rows missing an order_value column"),
    _user: dict = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Parse a shipment CSV and cross-reference each row against SLA penalty rules.

    Detects columns by name (case-insensitive, supports many aliases).
    Returns per-shipment findings plus aggregate summary and key insights.
    """
    content = await file.read()
    try:
        text = content.decode("utf-8-sig")  # handle BOM
    except UnicodeDecodeError:
        text = content.decode("latin-1")

    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames is None:
        raise HTTPException(status_code=422, detail="CSV appears to be empty or has no header row.")

    # Build header → canonical mapping
    col_map: Dict[str, str] = {}
    for h in reader.fieldnames:
        canonical = _resolve_col(h)
        if canonical:
            col_map[h] = canonical

    rows = list(reader)
    if not rows:
        raise HTTPException(status_code=422, detail="CSV has no data rows.")

    shipment_findings: List[Dict[str, Any]] = []
    total_penalty = 0.0
    breach_counts: Dict[str, int] = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0, "NONE": 0}
    total_delay = 0.0
    otif_values: List[float] = []
    on_time_count = 0

    for i, row in enumerate(rows):
        # Map row to canonical fields
        r: Dict[str, Any] = {}
        for h, canonical in col_map.items():
            r[canonical] = row.get(h, "")

        shipment_id = r.get("shipment_id") or f"ROW-{i + 1}"
        order_value = _safe_float(str(r.get("order_value", "")), default_order_value)
        delay_days  = _safe_float(str(r.get("delay_days", "0")))
        otif_raw    = r.get("otif_actual", "")
        otif_actual = _safe_float(str(otif_raw)) if otif_raw else None
        in_full     = _safe_float(str(r.get("in_full_pct", "100")), 100.0)
        ct          = str(r.get("contract_type", contract_type) or contract_type)
        tier        = str(r.get("customer_tier", customer_tier) or customer_tier)
        route       = str(r.get("route", ""))
        carrier     = str(r.get("carrier", ""))

        level = _breach_level(delay_days, otif_actual, otif_threshold)
        breach_counts[level] = breach_counts.get(level, 0) + 1

        # Penalty calculation
        penalty_amount = 0.0
        penalty_detail: Optional[Dict[str, Any]] = None
        if delay_days > 0 and order_value > 0:
            ctx_row = {
                "order_value":          order_value,
                "contract_type":        ct,
                "customer_tier":        tier,
                "predicted_delay_days": delay_days,
                "otif_actual_pct":      otif_actual,
                "otif_threshold_pct":   otif_threshold,
            }
            if penalty_rate is not None:
                ctx_row["nlp_extracted_penalty_rate"] = penalty_rate
            try:
                penalty_detail = _penalty_model.compute_with_detail(ctx_row, delay_days)
                penalty_amount = penalty_detail.get("financial_penalty", 0.0)
            except Exception:
                pass

        total_penalty += penalty_amount
        total_delay += delay_days
        if otif_actual is not None:
            otif_values.append(otif_actual)
        if delay_days == 0:
            on_time_count += 1

        shipment_findings.append({
            "shipment_id":    shipment_id,
            "order_value":    order_value,
            "delay_days":     delay_days,
            "otif_actual":    otif_actual,
            "in_full_pct":    in_full,
            "contract_type":  ct,
            "customer_tier":  tier,
            "route":          route,
            "carrier":        carrier,
            "breach_level":   level,
            "penalty_amount": round(penalty_amount, 2),
            "penalty_detail": penalty_detail,
        })

    n = len(rows)
    avg_otif = (sum(otif_values) / len(otif_values)) if otif_values else None
    avg_delay = total_delay / n if n else 0

    # Generate key insights
    insights: List[Dict[str, str]] = []
    critical_rows = [s for s in shipment_findings if s["breach_level"] == "CRITICAL"]
    if critical_rows:
        insights.append({
            "severity": "CRITICAL",
            "message": f"{len(critical_rows)} shipment(s) in CRITICAL breach — delay >14 days or OTIF <82%. Immediate review required.",
        })
    if avg_otif is not None and avg_otif < otif_threshold:
        gap = otif_threshold - avg_otif
        insights.append({
            "severity": "HIGH",
            "message": f"Portfolio OTIF {avg_otif:.1f}% is {gap:.1f}pp below the {otif_threshold}% threshold — cascading penalty multipliers may activate.",
        })
    if total_penalty > 0:
        insights.append({
            "severity": "MEDIUM",
            "message": f"Total contractual penalty exposure across {n} shipments: ${total_penalty:,.2f}.",
        })
    top_carrier_breaches: Dict[str, int] = {}
    for s in shipment_findings:
        if s["breach_level"] in ("CRITICAL", "HIGH") and s["carrier"]:
            top_carrier_breaches[s["carrier"]] = top_carrier_breaches.get(s["carrier"], 0) + 1
    for carrier_name, cnt in sorted(top_carrier_breaches.items(), key=lambda x: -x[1])[:3]:
        insights.append({
            "severity": "HIGH",
            "message": f"Carrier '{carrier_name}' accounts for {cnt} CRITICAL/HIGH breach(es) — consider SLA review.",
        })
    if on_time_count == n:
        insights.append({
            "severity": "NONE",
            "message": "All shipments delivered on time — no delay-based penalties triggered.",
        })

    detected_columns = list(set(col_map.values()))

    return {
        "total_shipments":    n,
        "on_time_count":      on_time_count,
        "breach_count":       n - on_time_count,
        "avg_otif_pct":       round(avg_otif, 2) if avg_otif is not None else None,
        "avg_delay_days":     round(avg_delay, 2),
        "total_penalty_usd":  round(total_penalty, 2),
        "breach_distribution": breach_counts,
        "otif_threshold_used": otif_threshold,
        "detected_columns":   detected_columns,
        "insights":           insights,
        "shipments":          shipment_findings,
    }


@router.post("/negotiate", summary="Stage 5+: LLM negotiation strategy from extracted clauses")
async def negotiate(
    body: SLANegotiateRequest,
    _user: dict = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Generates a data-driven supplier negotiation strategy.

    Pass `supplier_data` with performance metrics and optionally `contract_clauses`
    from a previous /sla/parse call. If clauses are omitted but
    `supplier_data.contract_text` is present, extraction runs automatically.
    """
    try:
        from app.financial_system.extensions.llm_negotiator import GenerativeNegotiator
        negotiator = GenerativeNegotiator()
        return await negotiator.generate_negotiation_payload(
            supplier_data=body.supplier_data,
            contract_clauses=body.contract_clauses,
            tenant_id=body.tenant_id,
        )
    except Exception as e:
        logger.error(f"SLA negotiate failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
