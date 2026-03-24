class ConstraintEngine:
    """
    Enforces real-world physical and capital limitations heavily onto the Solver matrix.
    """
    def __init__(self, max_liquidity):
        self.max_liquidity = max_liquidity
        self.current_spend = 0.0
        
    def is_valid(self, action_row):
        """
        Evaluates if selecting this action breaches catastrophic liquidity ceilings.
        """
        proposed_cost = action_row.get("total_cost", 0)
        
        if (self.current_spend + proposed_cost) > self.max_liquidity:
            return False # Hard Cash Constraint Breached
            
        return True
        
    def commit(self, action_row):
        """
        Actively deducts capital from the running solver pool.
        """
        self.current_spend += action_row.get("total_cost", 0)
