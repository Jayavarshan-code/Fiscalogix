def get_financial_twin_query():
    """
    FIX C (Critical): Added AND o.tenant_id = :tenant_id to every WHERE clause.
    WHAT WAS WRONG: The tenant_id parameter was accepted but never used in filtering.
    Every tenant could read every other tenant's financial data — a catastrophic
    multi-tenant data leak and a false SOC2 compliance claim.

    FIX C (Critical): Replaced CROSS JOIN with explicit JOIN on tenant_id.
    WHAT WAS WRONG: CROSS JOIN financial_parameters creates a Cartesian product.
    If financial_parameters has 2 rows (trivially happens on re-seed), every order
    is duplicated — silently doubling every financial metric on the dashboard.
    The UNIQUE(tenant_id) constraint on financial_parameters AND an explicit JOIN
    is the correct pattern for a per-tenant config table.

    FIX M1: Added carrier, route, cargo_type, industry_vertical, customer_tier,
    contract_type columns to the SELECT list so financial engines receive real
    data instead of always hitting default fallbacks.
    """
    return """
    SELECT
        o.order_id,
        o.tenant_id,
        o.order_month,
        s.shipment_id,
        o.customer_id,
        o.order_value,

        s.shipment_cost,
        s.delay_days,
        s.carrier,
        s.route,
        s.origin_node,
        s.destination_node,
        s.expected_arrival_utc,
        s.contract_type,

        sku.holding_cost_per_day,
        sku.cargo_type,
        sku.is_critical,
        sku.unit_value,

        fp.wacc,
        fp.penalty_rate,

        COALESCE(c.credit_days, 0)        AS credit_days,
        COALESCE(c.payment_delay_days, 0) AS payment_delay_days,
        COALESCE(c.customer_tier, 'standard') AS customer_tier,

        -- FIX: SELECT industry_vertical from shipments (set during ingestion)
        COALESCE(s.industry_vertical, 'default') AS industry_vertical,
        COALESCE(s.hs_code, sku.hs_code) AS hs_code,

        -- Derived financial columns
        (COALESCE(sku.holding_cost_per_day, 0) * s.delay_days)   AS holding_cost,
        (s.delay_days * fp.penalty_rate * o.order_value)          AS delay_cost,
        (o.order_value * fp.wacc)                            AS opportunity_cost,
        (o.order_value * fp.wacc
            * (COALESCE(c.credit_days, 0) + COALESCE(c.payment_delay_days, 0))
            / 365.0)                                         AS ar_cost,

        -- Total cost
        (
            s.shipment_cost
            + (COALESCE(sku.holding_cost_per_day, 0) * s.delay_days)
            + (s.delay_days * fp.penalty_rate * o.order_value)
            + (o.order_value * fp.wacc)
            + (o.order_value * fp.wacc
               * (COALESCE(c.credit_days, 0) + COALESCE(c.payment_delay_days, 0))
               / 365.0)
        ) AS total_cost,

        -- Contribution profit
        (
            o.order_value - (
                s.shipment_cost
                + (COALESCE(sku.holding_cost_per_day, 0) * s.delay_days)
                + (s.delay_days * fp.penalty_rate * o.order_value)
                + (o.order_value * fp.wacc)
                + (o.order_value * fp.wacc
                   * (COALESCE(c.credit_days, 0) + COALESCE(c.payment_delay_days, 0))
                   / 365.0)
            )
        ) AS contribution_profit

    FROM orders o
    JOIN shipments s ON o.order_id = s.order_id AND s.tenant_id = o.tenant_id
    LEFT JOIN sku  ON o.sku_id = sku.sku_id AND sku.tenant_id = o.tenant_id
    LEFT JOIN customers c ON o.customer_id = c.customer_id AND c.tenant_id = o.tenant_id
    -- FIX C: JOIN instead of CROSS JOIN; tenant-scoped config row, not Cartesian product
    JOIN financial_parameters fp ON fp.tenant_id = o.tenant_id
    WHERE o.tenant_id = :tenant_id
      AND (:shipment_id IS NULL OR s.shipment_id = :shipment_id)
    """


def get_dw_fallback_query():
    """
    Fallback query for tenants who uploaded data via bulk CSV ingestion.
    CSV data lands in dw_shipment_facts, not in the OLTP orders/shipments tables.
    This query projects dw_shipment_facts into the same column shape as
    get_financial_twin_query() so all downstream pipeline stages work unchanged.
    Uses COALESCE(fp.wacc, 0.085) / COALESCE(fp.penalty_rate, 0.02) so the
    query works even when financial_parameters has no row for the tenant.
    """
    return """
    SELECT
        COALESCE(dw.raw_source_uuid, CAST(dw.id AS TEXT))             AS order_id,
        dw.tenant_id,
        EXTRACT(MONTH FROM dw.created_at)                              AS order_month,
        COALESCE(dw.raw_source_uuid, CAST(dw.id AS TEXT))             AS shipment_id,
        'CSV-Import'                                                   AS customer_id,
        COALESCE(dw.total_value_usd, 0)                               AS order_value,
        COALESCE(dw.total_cost_usd, dw.total_value_usd * 0.15, 0)    AS shipment_cost,
        COALESCE(dw.delay_days_calculated, 0)                         AS delay_days,
        COALESCE(dw.carrier, 'unknown')                               AS carrier,
        COALESCE(dw.route, 'domestic')                                AS route,
        dw.origin_node,
        dw.destination_node,
        dw.expected_arrival_utc,
        COALESCE(dw.contract_type, 'standard')                        AS contract_type,
        0.003                                                         AS holding_cost_per_day,
        COALESCE(dw.cargo_type, 'general_cargo')                      AS cargo_type,
        FALSE                                                         AS is_critical,
        COALESCE(dw.total_value_usd, 0)                               AS unit_value,
        COALESCE(fp.wacc, 0.085)                                      AS wacc,
        COALESCE(fp.penalty_rate, 0.02)                               AS penalty_rate,
        COALESCE(dw.credit_days, 30)                                  AS credit_days,
        0                                                             AS payment_delay_days,
        COALESCE(dw.customer_tier, 'standard')                        AS customer_tier,
        COALESCE(dw.industry_vertical, 'default')                     AS industry_vertical,
        NULL                                                          AS hs_code,

        0.003 * COALESCE(dw.delay_days_calculated, 0)                                                                          AS holding_cost,
        COALESCE(dw.delay_days_calculated, 0) * COALESCE(fp.penalty_rate, 0.02) * COALESCE(dw.total_value_usd, 0)             AS delay_cost,
        COALESCE(dw.total_value_usd, 0) * COALESCE(fp.wacc, 0.085)                                                            AS opportunity_cost,
        COALESCE(dw.total_value_usd, 0) * COALESCE(fp.wacc, 0.085) * COALESCE(dw.credit_days, 30) / 365.0                    AS ar_cost,

        (
            COALESCE(dw.total_cost_usd, dw.total_value_usd * 0.15, 0)
            + 0.003 * COALESCE(dw.delay_days_calculated, 0)
            + COALESCE(dw.delay_days_calculated, 0) * COALESCE(fp.penalty_rate, 0.02) * COALESCE(dw.total_value_usd, 0)
            + COALESCE(dw.total_value_usd, 0) * COALESCE(fp.wacc, 0.085)
            + COALESCE(dw.total_value_usd, 0) * COALESCE(fp.wacc, 0.085) * COALESCE(dw.credit_days, 30) / 365.0
        )                                                             AS total_cost,

        COALESCE(
            dw.margin_usd,
            dw.total_value_usd - COALESCE(dw.total_cost_usd, dw.total_value_usd * 0.15, 0)
        )                                                             AS contribution_profit

    FROM dw_shipment_facts dw
    LEFT JOIN financial_parameters fp ON fp.tenant_id = dw.tenant_id
    WHERE dw.tenant_id = :tenant_id
      AND (:shipment_id IS NULL OR dw.raw_source_uuid = CAST(:shipment_id AS TEXT))
    ORDER BY dw.created_at DESC
    LIMIT 5000
    """


def get_inventory_twin_query():
    """
    FIX C: Same CROSS JOIN fix applied. Replaced with explicit tenant-scoped JOIN.
    FIX C: Added AND i.tenant_id = :tenant_id to WHERE clause.
    """
    return """
    SELECT
        i.inventory_id,
        i.sku_id,
        i.warehouse_id,
        i.quantity,
        sku.unit_cost,
        fp.wacc,

        (i.quantity * sku.unit_cost) AS capital_locked,

        (
            (i.quantity * sku.unit_cost) * fp.wacc * (30.0 / 365)
        ) AS inventory_opportunity_cost

    FROM inventory i
    JOIN sku ON i.sku_id = sku.sku_id AND sku.tenant_id = i.tenant_id
    -- FIX C: JOIN instead of CROSS JOIN
    JOIN financial_parameters fp ON fp.tenant_id = i.tenant_id
    WHERE i.tenant_id = :tenant_id
      AND (:warehouse_id IS NULL OR i.warehouse_id = :warehouse_id)
    """
