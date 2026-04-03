from typing import Dict, Any, List, Optional
from .spatial_h3_service import SpatialH3Service
from .llm_gateway import LlmGateway, AgentResponse

class CopilotService:
    """
    The High-Level Orchestrator for the Logistics Copilot.
    Fuses Spatial Intelligence (H3) with Generative Reasoning (LLM).
    """
    
    def __init__(self, h3_service: SpatialH3Service, llm_gateway: LlmGateway):
        self.h3 = h3_service
        self.llm = llm_gateway
        self.risk_matrix: Dict[str, Any] = {} # Mocked H3 Risk Matrix

    def update_risk_matrix(self, new_risks: Dict[str, Any]):
        """Updates the internal spatial risk state."""
        self.risk_matrix.update(new_risks)

    async def analyze_shipment_position(self, 
                                      lat: float, 
                                      lon: float, 
                                      shipment_id: str,
                                      telemetry: Dict[str, Any]) -> AgentResponse:
        """
        Main entry point for H3-aware spatial reasoning.
        1. Resolves Lat/Lon to H3.
        2. Fetches localized risk context (neighbors).
        3. Generates simplified strategic advice via LLM.
        """
        # Step 1: Resolve H3 ID
        h3_id = self.h3.geo_to_h3(lat, lon)
        
        # Step 2: Extract Spatial Context (Neighbors/Local Risks)
        risk_context = self.h3.get_risk_context(h3_id, self.risk_matrix)
        
        # Step 3: Call LLM with enriched context
        return await self.llm.interpret_spatial_risk(
            h3_id=h3_id,
            risk_context=risk_context,
            telemetry=telemetry
        )

    async def get_emergency_reroute_advice(self, 
                                          shipment_id: str, 
                                          current_lat: float, 
                                          current_lon: float,
                                          efi_data: Dict[str, Any]) -> AgentResponse:
        """
        Fuses H3 spatial context with EFI financial impact for high-stakes decisions.
        """
        h3_id = self.h3.geo_to_h3(current_lat, current_lon)
        risk_context = self.h3.get_risk_context(h3_id, self.risk_matrix)
        
        return await self.llm.get_integrated_copilot_advice(
            h3_id=h3_id,
            risk_context=risk_context,
            efi_data=efi_data,
            doc_status="VERIFIED" # Mocked
        )

    async def verify_physical_anomaly(self, 
                                     image_data: str, 
                                     shipment_id: str, 
                                     context: str) -> AgentResponse:
        """
        Processes physical image evidence to confirm or refute a risk event.
        e.g., 'Analyzing photo of container #402 ... confirms severe puncture damage.'
        """
        return await self.llm.analyze_visual_evidence(
            image_data=image_data,
            context=f"Shipment {shipment_id}: {context}",
            task_type="anomaly_verification"
        )
