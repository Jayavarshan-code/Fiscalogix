def get_financial_twin_query():
    return """
    SELECT 
        o.order_id,
        s.shipment_id,
        o.customer_id,
        o.order_value,

        s.shipment_cost,
        s.delay_days,
        sku.holding_cost_per_day,
        fp.wacc,
        fp.penalty_rate,
        sku.is_critical,
        sku.unit_value,
        COALESCE(c.credit_days, 0) AS credit_days,
        COALESCE(c.payment_delay_days, 0) AS payment_delay_days,

        -- derived
        (sku.holding_cost_per_day * s.delay_days) AS holding_cost,
        (s.delay_days * fp.penalty_rate * o.order_value) AS delay_cost,
        (o.order_value * fp.wacc) AS opportunity_cost,
        (o.order_value * fp.wacc * (COALESCE(c.credit_days, 0) + COALESCE(c.payment_delay_days, 0)) / 365.0) AS ar_cost,

        -- total
        (
            s.shipment_cost +
            (sku.holding_cost_per_day * s.delay_days) +
            (s.delay_days * fp.penalty_rate * o.order_value) +
            (o.order_value * fp.wacc) +
            (o.order_value * fp.wacc * (COALESCE(c.credit_days, 0) + COALESCE(c.payment_delay_days, 0)) / 365.0)
        ) AS total_cost,

        -- profit
        (
            o.order_value -
            (
                s.shipment_cost +
                (sku.holding_cost_per_day * s.delay_days) +
                (s.delay_days * fp.penalty_rate * o.order_value) +
                (o.order_value * fp.wacc) +
                (o.order_value * fp.wacc * (COALESCE(c.credit_days, 0) + COALESCE(c.payment_delay_days, 0)) / 365.0)
            )
        ) AS contribution_profit

    FROM orders o
    JOIN shipments s ON o.order_id = s.order_id
    JOIN sku ON o.sku_id = sku.sku_id
    LEFT JOIN customers c ON o.customer_id = c.customer_id
    CROSS JOIN financial_parameters fp
    WHERE (:shipment_id IS NULL OR s.shipment_id = :shipment_id)
    """

def get_inventory_twin_query():
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
    JOIN sku ON i.sku_id = sku.sku_id
    CROSS JOIN financial_parameters fp

    WHERE (:warehouse_id IS NULL OR i.warehouse_id = :warehouse_id)
    """
