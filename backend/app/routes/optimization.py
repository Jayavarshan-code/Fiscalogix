from fastapi import APIRouter
from pydantic import BaseModel
from typing import Dict, List, Any
from app.job_manager import JobManager

router = APIRouter(prefix="/optimization", tags=["Mathematical Solvers Queue"])

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
    Dispatches a heavy MILP solver to the background Process Pool.
    Returns instantly with a Job ID.
    """
    job_id = await JobManager.dispatch_network_routing({
        "origins": payload.origins,
        "destinations": payload.destinations,
        "supply": payload.supply,
        "demand": payload.demand,
        "costs": payload.costs,
        "capacities": payload.capacities
    })
    return {"status": "accepted", "job_id": job_id, "message": "Optimization added to background math queue."}

class InventoryOptimizationRequest(BaseModel):
    service_level: float = 0.95
    nodes: List[Dict[str, Any]]

@router.post("/inventory_meio")
async def optimize_inventory(payload: InventoryOptimizationRequest):
    job_id = await JobManager.dispatch_meio({
        "nodes": payload.nodes,
        "service_level": payload.service_level
    })
    return {"status": "accepted", "job_id": job_id}

class MonteCarloRequest(BaseModel):
    legs: List[Dict[str, float]]
    target_arrival_days: int
    simulations: int = 10000

@router.post("/monte_carlo_risk")
async def monte_carlo_risk(payload: MonteCarloRequest):
    job_id = await JobManager.dispatch_monte_carlo({
        "legs": payload.legs,
        "target_arrival_days": payload.target_arrival_days,
        "simulations": payload.simulations
    })
    return {"status": "accepted", "job_id": job_id}

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
    job_id = await JobManager.dispatch_step_cost({
        "origins": payload.origins,
        "destinations": payload.destinations,
        "supply": payload.supply,
        "demand": payload.demand,
        "base_costs": payload.base_costs,
        "discounted_costs": payload.discounted_costs,
        "volume_thresholds": payload.volume_thresholds,
        "capacities": payload.capacities
    })
    return {"status": "accepted", "job_id": job_id}

@router.get("/status/{job_id}")
async def get_job_status(job_id: str):
    """
    Polling endpoint for the frontend to check if the math process has completed.
    Returns {"status": "PROCESSING"} or {"status": "COMPLETED", "result": {...}}
    """
    return JobManager.get_job_status(job_id)
