import logging
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Dict, List, Any
from app.job_manager import JobManager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/optimization", tags=["Mathematical Solvers Queue"])


# ── helpers ───────────────────────────────────────────────────────────────────

def _inline_result(result: Any) -> Dict[str, Any]:
    """Wraps a synchronous result to match the async job response shape."""
    return {"status": "completed", "job_id": None, "result": result}


def _accepted(job_id: str) -> Dict[str, Any]:
    return {"status": "accepted", "job_id": job_id}


# ── Network Routing ───────────────────────────────────────────────────────────

class NetworkOptimizationRequest(BaseModel):
    origins: List[str]
    destinations: List[str]
    supply: Dict[str, int]
    demand: Dict[str, int]
    costs: Dict[str, Dict[str, float]]
    capacities: Dict[str, Dict[str, int]]


@router.post("/network")
async def optimize_network(payload: NetworkOptimizationRequest):
    """
    Dispatches a MILP solver to Celery.
    Falls back to inline synchronous execution when the broker is unavailable.
    """
    kwargs = {
        "origins": payload.origins,
        "destinations": payload.destinations,
        "supply": payload.supply,
        "demand": payload.demand,
        "costs": payload.costs,
        "capacities": payload.capacities,
    }
    try:
        job_id = await JobManager.dispatch_network_routing(kwargs)
        return _accepted(job_id)
    except Exception as e:
        logger.warning(f"Celery unavailable for network routing ({e}). Running inline.")
        from app.financial_system.optimizations.network_routing import NetworkRoutingEngine
        return _inline_result(NetworkRoutingEngine.optimize(**kwargs))


# ── Inventory MEIO ────────────────────────────────────────────────────────────

class InventoryOptimizationRequest(BaseModel):
    service_level: float = 0.95
    nodes: List[Dict[str, Any]]


def _normalize_meio_nodes(nodes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Maps frontend field names to MEIOEngine field names.
    Frontend sends: demand_mean, demand_std, lead_time_days, holding_cost
    Engine expects: avg_daily_demand, std_dev_demand, avg_lead_time_days, std_dev_lead_time
    """
    normalized = []
    for n in nodes:
        normalized.append({
            "node_id":            n.get("node_id"),
            "avg_daily_demand":   n.get("avg_daily_demand") or n.get("demand_mean", 100),
            "std_dev_demand":     n.get("std_dev_demand")   or n.get("demand_std", 15),
            "avg_lead_time_days": n.get("avg_lead_time_days") or n.get("lead_time_days", 14),
            "std_dev_lead_time":  n.get("std_dev_lead_time", 2),
            "holding_cost":       n.get("holding_cost", 10),
        })
    return normalized


@router.post("/inventory_meio")
async def optimize_inventory(payload: InventoryOptimizationRequest):
    nodes = _normalize_meio_nodes(payload.nodes)
    kwargs = {"nodes": nodes, "service_level": payload.service_level}
    try:
        job_id = await JobManager.dispatch_meio(kwargs)
        return _accepted(job_id)
    except Exception as e:
        logger.warning(f"Celery unavailable for MEIO ({e}). Running inline.")
        from app.financial_system.optimizations.multi_echelon_inventory import MEIOEngine
        return _inline_result(MEIOEngine.optimize(**kwargs))


# ── Monte Carlo Risk ──────────────────────────────────────────────────────────

class MonteCarloRequest(BaseModel):
    legs: List[Dict[str, float]]
    target_arrival_days: int
    simulations: int = 10000


def _normalize_mc_legs(legs: List[Dict[str, float]]) -> List[Dict[str, float]]:
    """
    Maps frontend field names to MonteCarloRiskEngine field names.
    Frontend sends: mean_days, std_days, cost_per_day
    Engine expects: avg_days, std_dev
    """
    normalized = []
    for leg in legs:
        normalized.append({
            "avg_days": leg.get("avg_days") or leg.get("mean_days", 7.0),
            "std_dev":  leg.get("std_dev")  or leg.get("std_days", 1.0),
            **{k: v for k, v in leg.items() if k not in ("mean_days", "std_days", "avg_days", "std_dev")},
        })
    return normalized


@router.post("/monte_carlo_risk")
async def monte_carlo_risk(payload: MonteCarloRequest):
    legs = _normalize_mc_legs(payload.legs)
    kwargs = {
        "legs": legs,
        "target_arrival_days": payload.target_arrival_days,
        "simulations": payload.simulations,
    }
    try:
        job_id = await JobManager.dispatch_monte_carlo(kwargs)
        return _accepted(job_id)
    except Exception as e:
        logger.warning(f"Celery unavailable for Monte Carlo ({e}). Running inline.")
        from app.financial_system.optimizations.monte_carlo_risk import MonteCarloRiskEngine
        return _inline_result(MonteCarloRiskEngine.simulate(**kwargs))


# ── Step-Cost Network ─────────────────────────────────────────────────────────

class StepCostOptimizationRequest(BaseModel):
    origins: List[str]
    destinations: List[str]
    supply: Dict[str, int]
    demand: Dict[str, int]
    base_costs: Dict[str, Dict[str, float]]
    discounted_costs: Dict[str, Dict[str, float]]
    volume_thresholds: Dict[str, Dict[str, int]]
    capacities: Dict[str, Dict[str, int]]


@router.post("/network_step_cost")
async def optimize_network_step_cost(payload: StepCostOptimizationRequest):
    kwargs = {
        "origins": payload.origins,
        "destinations": payload.destinations,
        "supply": payload.supply,
        "demand": payload.demand,
        "base_costs": payload.base_costs,
        "discounted_costs": payload.discounted_costs,
        "volume_thresholds": payload.volume_thresholds,
        "capacities": payload.capacities,
    }
    try:
        job_id = await JobManager.dispatch_step_cost(kwargs)
        return _accepted(job_id)
    except Exception as e:
        logger.warning(f"Celery unavailable for step-cost routing ({e}). Running inline.")
        from app.financial_system.optimizations.step_cost_routing import StepCostRoutingEngine
        return _inline_result(StepCostRoutingEngine.optimize(**kwargs))


# ── Status polling ────────────────────────────────────────────────────────────

@router.get("/status/{job_id}")
async def get_job_status(job_id: str):
    """
    Frontend polls this every 2s after receiving a job_id.
    Returns {"status": "PROCESSING"} | {"status": "COMPLETED", "result": {...}} | {"status": "FAILED", "error": "..."}
    """
    return JobManager.get_job_status(job_id)
