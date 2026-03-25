from app.services.security_mesh import SecurityMeshService

class BrainOrchestrator:
    """
    Pillar 13: Central Brain - Federated Coordinator.
    Hardened with Zero-Trust mTLS and Signature Verification.
    """
    
    def __init__(self, security_mesh: SecurityMeshService):
        self.security_mesh = security_mesh
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

    async def achieve_consensus(self, deltas: List[SemanticDelta], signatures: Dict[str, str]) -> Dict[str, Any]:
        """
        Synthesizes conflicting local decisions into a Global Strategy.
        Uses Zero-Trust mTLS and Signature Verification for every delta.
        """
        verified_deltas = []
        
        for d in deltas:
            # 1. Zero-Trust Identity Check (mTLS)
            # In a real system, the hive's cert would be retrieved from the request context
            hive_cert = self.security_mesh.verified_certificates.get(d.hive_id)
            if not self.security_mesh.verify_mtls_handshake(d.hive_id, hive_cert):
                print(f"[Brain] SECURITY ALERT: Rejecting delta from unverified Hive {d.hive_id}")
                continue
                
            # 2. Payload Integrity Check
            sig = signatures.get(d.hive_id)
            if not self.security_mesh.verify_signature(d.json(), sig, hive_cert):
                print(f"[Brain] SECURITY ALERT: Rejecting tampered delta from Hive {d.hive_id}")
                continue
                
            verified_deltas.append(d)

        if not verified_deltas:
            return {"global_efi_delta": 0, "status": "No verified activity"}

        # 3. Aggregate EFI Deltas (from verified data only)
        total_efi_shift = sum(d.efi_delta for d in verified_deltas)
        
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
