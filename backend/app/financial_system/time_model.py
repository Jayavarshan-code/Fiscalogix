class TimeValueModel:
    """
    Calculates two distinct time-based costs:
    1. Financial Cost of Capital (Opportunity Cost) = wacc * (delay / 365) * order_value
    2. Physical Pipeline Holding Cost (Insurance/Storage) = holding_rate * (delay / 365) * total_cost
    """
    def compute(self, row, predicted_delay):
        # 1. Capital Tied Up (Opportunity Cost on delayed Revenue)
        wacc = row.get("wacc", 0.08) # Default 8% Cost of Capital
        order_value = row.get("order_value", 0.0)
        capital_cost = order_value * wacc * (predicted_delay / 365.0)
        
        # 2. Physical Holding/Pipeline Cost (Insurance, warehousing for delayed goods)
        # Industry average holding cost is 20% annualized
        holding_rate = 0.20
        total_cost = row.get("total_cost", 0.0)
        pipeline_cost = total_cost * holding_rate * (predicted_delay / 365.0)
        
        return round(capital_cost + pipeline_cost, 2)

