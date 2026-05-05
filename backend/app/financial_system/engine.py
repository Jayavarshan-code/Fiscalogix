import logging
from sqlalchemy import text
from app.Db.connections import engine
from app.financial_system.queries import get_financial_twin_query, get_dw_fallback_query

logger = logging.getLogger(__name__)


class FinancialCoreEngine:

    def compute(self, shipment_id: int = None, tenant_id: str = "default_tenant"):
        params = {"shipment_id": shipment_id, "tenant_id": tenant_id}

        with engine.connect() as conn:
            rows = [dict(r._mapping) for r in conn.execute(text(get_financial_twin_query()), params)]

        if rows:
            return rows

        # OLTP tables empty — tenant uploaded via bulk CSV, data is in dw_shipment_facts.
        logger.info("FinancialCoreEngine: OLTP empty for tenant=%s, falling back to dw_shipment_facts", tenant_id)
        with engine.connect() as conn:
            rows = [dict(r._mapping) for r in conn.execute(text(get_dw_fallback_query()), params)]

        return rows
