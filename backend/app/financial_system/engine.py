from sqlalchemy import text
from app.Db.connections import engine
from app.financial_system.queries import get_financial_twin_query

class FinancialCoreEngine:

    def compute(self, shipment_id: int = None, tenant_id: str = "default_tenant"):
        query = get_financial_twin_query()
        with engine.connect() as conn:
            result = conn.execute(
                text(query),
                {"shipment_id": shipment_id, "tenant_id": tenant_id}
            )
            return [dict(row._mapping) for row in result]
