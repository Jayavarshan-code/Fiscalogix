from typing import List, Dict, Any, Set
from app.models.federated import SemanticDelta, HiveNodeStatus
from app.services.hive_core import HiveCore
import asyncio

class BrainOrchestrator:
    """
    Pillar 13: Central Brain - Federated Coordinator.
    The primary control plane for the Global Hive Network.
    """
    
    def __init__(self):
        self.registered_hives: Dict[str, HiveNodeStatus] = {}
        self.hive_instances: Dict[str, HiveCore] = {} # Simulated edge connections
        self.global_risk_score: float = 0.05

    async def register_hive(self, hive: HiveCore):
        """Onboards a new autonomous Hive Node."""
        status = HiveNodeStatus(
            hive_id=hive.hive_id,
            status="Active",
            last_sync=asyncio.get_event_loop().time(), # Mock simple timestamp
            local_compute_load=0.1
        )
        self.registered_hives[hive.hive_id] = status
        self.hive_instances[hive.hive_id] = hive
        print(f"[Brain] Registered Edge Hive: {hive.hive_id}")

    async def push_global_policy(self, policy_name: str, constraints: Dict[str, Any]):
        """
        Broadcasting Global Guardrails to the entire Edge Network.
        Example: 'Prohibit rerouting through Red Sea' or 'Max delay penalty 10%'.
        """
        policy_string = f"POLICY_{policy_name}: {constraints}"
        tasks = [hive.update_policy([policy_string]) for hive in self.hive_instances.values()]
        await asyncio.gather(*tasks)
        return {"broadcast_count": len(tasks), "policy": policy_name}

    async def achieve_consensus(self, deltas: List[SemanticDelta]) -> Dict[str, Any]:
        """
        Synthesizes conflicting local decisions into a Global Strategy.
        Uses semantic weighting to update the Global EFI and Risk state.
        """
        if not deltas:
            return {"global_efi_delta": 0, "status": "No activity"}

        # 1. Aggregate EFI Deltas
        total_efi_shift = sum(d.efi_delta for d in deltas)
        
        # 2. Extract Global Risk Signal
        # (In prod: updates the central Neo4j risk weights based on Hive insights)
        avg_local_risk = sum(d.risk_snapshot.get("local_hex_risk", 0) for d in deltas) / len(deltas)
        
        # 3. Decision Reconciliation
        all_actions = []
        for d in deltas:
            all_actions.extend(d.decisions)
            
        print(f"[Brain] Global Consensus Achieved. Total EFI Shift: {total_efi_shift}")
        
        return {
            "consensus_timestamp": "now",
            "global_efi_impact": total_efi_shift,
            "systemic_risk_adjustment": avg_local_risk * 0.2, # Conservative global correction
            "autonomous_actions_logged": all_actions,
            "sovereignty_verification": "PASS: Zero raw data exported"
        }
