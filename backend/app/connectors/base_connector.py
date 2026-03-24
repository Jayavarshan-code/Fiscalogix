from abc import ABC, abstractmethod
from typing import List, Dict, Any

class BaseERPConnector(ABC):
    """
    Abstract Base Class for Enterprise Resource Planning (ERP) integrations.
    Enforces a strict contract for ingesting supply chain data automatically.
    """
    
    @abstractmethod
    def authenticate(self) -> bool:
        """Authenticates with the ERP system."""
        pass
        
    @abstractmethod
    def fetch_orders(self, tenant_id: str) -> List[Dict[str, Any]]:
        """Extracts sales and purchase orders from the ERP."""
        pass
        
    @abstractmethod
    def fetch_inventory(self, tenant_id: str) -> List[Dict[str, Any]]:
        """Extracts current warehouse inventory states."""
        pass
        
    @abstractmethod
    async def execute_action(self, tenant_id: str, action_type: str, payload: dict) -> dict:
        """
        Write-back execution API. 
        Pushes a structural decision (e.g. REROUTE) back to the ERP.
        Must return the ERP's confirmation receipt.
        """
        pass
