import h3
from typing import List, Tuple, Dict, Any

class SpatialH3Service:
    """
    Core H3 utility service for hexagonal spatial indexing.
    Enables O(1) spatial joins and proximity reasoning.
    """
    
    def __init__(self, default_res: int = 7):
        self.default_res = default_res

    def geo_to_h3(self, lat: float, lng: float, res: int = None) -> str:
        """Converts coordinates to an H3 index ID."""
        r = res or self.default_res
        return h3.geo_to_h3(lat, lng, r)

    def h3_to_geo(self, h3_id: str) -> Tuple[float, float]:
        """Converts an H3 index back to coordinates."""
        return h3.h3_to_geo(h3_id)

    def get_neighbors(self, h3_id: str, k: int = 1) -> List[str]:
        """Returns neighboring cells within k-distance."""
        return list(h3.k_ring(h3_id, k))

    def get_risk_context(self, h3_id: str, risk_matrix: Dict[str, Any]) -> List[str]:
        """
        Translates raw H3 cell state into a human-readable risk description.
        Used to feed the LLM context.
        """
        neighbors = self.get_neighbors(h3_id, k=1)
        active_risks = []
        
        for cell in neighbors:
            if cell in risk_matrix:
                risk_info = risk_matrix[cell]
                relation = "current location" if cell == h3_id else "nearby zone"
                active_risks.append(f"Risk in {relation} ({cell}): {risk_info.get('type')} - {risk_info.get('severity')} severity.")
        
        return active_risks

    def simplify_cell_id(self, h3_id: str) -> str:
        """Returns a shortened, easier-to-read version of the H3 ID."""
        return f"Zone-{h3_id[-6:]}"
