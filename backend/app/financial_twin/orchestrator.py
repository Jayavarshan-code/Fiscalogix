import datetime
from app.financial_twin.engine import FinancialTwinEngine
from app.financial_twin.aggregators import FinancialAggregator

class FinancialTwinOrchestrator:

    def __init__(self):
        self.engine = FinancialTwinEngine()
        self.aggregator = FinancialAggregator()

    def run_shipments(self, shipment_id: int = None):
        data = self.engine.compute_shipments(shipment_id=shipment_id)
        summary = self.aggregator.summarize_shipments(data)

        return {
            "summary": summary,
            "records": data
        }

    def run_inventory(self, warehouse_id: int = None):
        data = self.engine.compute_inventory(warehouse_id=warehouse_id)
        summary = self.aggregator.summarize_inventory(data)

        return {
            "summary": summary,
            "records": data
        }
        
    def snapshot_state(self):
        """
        Creates a point-in-time snapshot of the complete financial twin state.
        This represents the "STATE LAYER" for historical tracking.
        """
        shipment_data = self.run_shipments()
        inventory_data = self.run_inventory()
        
        snapshot = {
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "total_profit": shipment_data["summary"]["total_profit"],
            "total_capital_locked": inventory_data["summary"]["total_capital_locked"],
            "total_inventory_opportunity_cost": inventory_data["summary"]["total_inventory_opportunity_cost"],
            "total_ar_cost": shipment_data["summary"]["total_ar_cost"]
        }
        
        # Here we would normally save to db, e.g., insertion into `financial_twin_snapshots`
        return snapshot