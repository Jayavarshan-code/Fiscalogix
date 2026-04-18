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

    return SLAParseResponse(**{k: extraction[k] for k in SLAParseResponse.model_fields if k in extraction})


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

    return SLAParseResponse(**{k: extraction[k] for k in SLAParseResponse.model_fields if k in extraction})


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
    parse_resp = SLAParseResponse(**{k: extraction[k] for k in SLAParseResponse.model_fields if k in extraction})

    return SLAAnalysisResult(
        contract_text_preview=raw_text[:400],
        extraction=parse_resp,
        penalty=penalty,
        risk_score=risk_score,
        severity_distribution=sev_dist,
        top_bottlenecks=top_bottlenecks,
        processing_pipeline=pipeline,
    )


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
