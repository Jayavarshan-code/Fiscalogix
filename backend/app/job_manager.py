from typing import Dict, Any
from app.tasks import (
    task_optimize_network_routing,
    task_optimize_meio,
    task_monte_carlo_risk,
    task_optimize_step_cost
)
from app.celery_app import celery_app

class JobManager:
    @staticmethod
    def get_job_status(job_id: str) -> Dict[str, Any]:
        """
        Interrogates the Redis result backend for the Celery Task ID.
        """
        task_result = celery_app.AsyncResult(job_id)
        
        if task_result.state == 'PENDING':
            return {"status": "PROCESSING", "progress": 0}
        elif task_result.state == 'SUCCESS':
            return {"status": "COMPLETED", "progress": 100, "result": task_result.result}
        elif task_result.state == 'FAILURE':
            return {"status": "FAILED", "error": str(task_result.info)}
            
        return {"status": task_result.state}

    @staticmethod
    async def dispatch_network_routing(kwargs: Dict[str, Any]) -> str:
        task = task_optimize_network_routing.delay(kwargs)
        return task.id

    @staticmethod
    async def dispatch_meio(kwargs: Dict[str, Any]) -> str:
        task = task_optimize_meio.delay(kwargs)
        return task.id
        
    @staticmethod
    async def dispatch_monte_carlo(kwargs: Dict[str, Any]) -> str:
        task = task_monte_carlo_risk.delay(kwargs)
        return task.id

    @staticmethod
    async def dispatch_step_cost(kwargs: Dict[str, Any]) -> str:
        task = task_optimize_step_cost.delay(kwargs)
        return task.id
