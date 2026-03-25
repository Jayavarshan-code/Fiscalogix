import hashlib
import time
from typing import Dict, Any, Optional

class SecurityMeshService:
    """
    Pillar 13 Security Header: Global Identity Mesh (Zero-Trust).
    Enforces Mutual TLS (mTLS) for all Federated Hive communications.
    """
    
    def __init__(self, brain_secret: str = "FISCALOGIX_ROOT_CA_2026"):
        self.brain_secret = brain_secret
        self.verified_certificates: Dict[str, str] = {} # {hive_id: cert_hash}

    def generate_hive_certificate(self, hive_id: str) -> str:
        """
        Simulates the issuance of a signed Hive Certificate.
        In production, this would be a real X.509 cert.
        """
        raw_val = f"{hive_id}:{self.brain_secret}:{time.time()}"
        cert_hash = hashlib.sha256(raw_val.encode()).hexdigest()
        self.verified_certificates[hive_id] = cert_hash
        return cert_hash

    def verify_mtls_handshake(self, hive_id: str, presented_cert: str) -> bool:
        """
        Enforces Zero-Trust: Both sides must be verified.
        1. Check if Hive ID is registered.
        2. Verify that the presented certificate matches the Brain's CA record.
        """
        known_cert = self.verified_certificates.get(hive_id)
        if not known_cert:
            print(f"[Security] UNREGISTERED HIVE ATTEMPT: {hive_id}")
            return False
            
        if known_cert != presented_cert:
            print(f"[Security] MUTUAL TLS FAILURE: Certificate Mismatch for {hive_id}")
            return False
            
        return True

    def sign_payload(self, payload: str, cert: str) -> str:
        """Signs a SemanticDelta for integrity verification."""
        return hashlib.sha256(f"{payload}:{cert}".encode()).hexdigest()

    def verify_signature(self, payload: str, signature: str, cert: str) -> bool:
        """Verifies that the payload hasn't been tampered with during transit."""
        expected = self.sign_payload(payload, cert)
        return expected == signature
