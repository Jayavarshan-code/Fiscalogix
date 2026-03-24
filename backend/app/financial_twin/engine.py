from sqlalchemy import text
from app.Db.connections import engine
from app.financial_twin.queries import get_financial_twin_query, get_inventory_twin_query

class FinancialTwinEngine:

    def compute_shipments(self, shipment_id: int = None, tenant_id: str = "default_tenant"):
        query = get_financial_twin_query()
        with engine.connect() as conn:
            result = conn.execute(
                text(query),
                {"shipment_id": shipment_id, "tenant_id": tenant_id}
            )
            return [dict(row._mapping) for row in result]

    def compute_inventory(self, warehouse_id: int = None, tenant_id: str = "default_tenant"):
        query = get_inventory_twin_query()
        with engine.connect() as conn:
            result = conn.execute(
                text(query),
                {"warehouse_id": warehouse_id, "tenant_id": tenant_id}
            )
            return [dict(row._mapping) for row in result]