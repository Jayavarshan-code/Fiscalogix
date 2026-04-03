import React from 'react';
import { DollarSign, Package, Activity, AlertTriangle, ShieldCheck } from 'lucide-react';

interface CostBreakdown {
  delay_cost: number;
  penalty_cost: number;
  inventory_holding: number;
  opportunity_cost: number;
}

interface CostBreakdownTableProps {
  breakdown: CostBreakdown;
  total: number;
}

export const CostBreakdownTable: React.FC<CostBreakdownTableProps> = ({ breakdown, total }) => {
  const getIcon = (category: string) => {
    if (category === 'delay_cost') return <Activity size={14} />;
    if (category === 'penalty_cost') return <AlertTriangle size={14} />;
    if (category === 'inventory_holding') return <Package size={14} />;
    return <DollarSign size={14} />;
  };

  const getLabel = (category: string) => {
    const formatted = category.replace(/_/g, ' ');
    return formatted.charAt(0).toUpperCase() + formatted.slice(1);
  };

  return (
    <div className="cost-breakdown-panel mt-4 p-6 glass-panel">
      <div className="flex items-center gap-2 mb-6">
        <ShieldCheck size={16} className="text-brand-accent" />
        <h4 className="text-[11px] font-black text-secondary uppercase tracking-widest">Financial Leakage Audit</h4>
      </div>

      <div className="space-y-4">
        {Object.entries(breakdown).map(([category, cost], i) => (
          <div key={i} className="space-y-2">
            <div className="flex justify-between items-center text-[12px] font-semibold">
              <div className="flex items-center gap-2 text-secondary">
                {getIcon(category)}
                <span>{getLabel(category)}</span>
              </div>
              <span className="font-mono text-primary">₹{cost.toLocaleString()}</span>
            </div>
            <div className="h-1.5 bg-subtle rounded-full overflow-hidden">
              <div 
                className="h-full bg-brand-accent transition-all duration-1000" 
                style={{ width: `${(cost / total) * 100}%` }}
              ></div>
            </div>
          </div>
        ))}
      </div>

      <div className="mt-6 pt-6 border-t border-subtle flex justify-between items-center">
        <span className="text-[11px] font-black text-muted uppercase tracking-widest">Total EFI Exposure</span>
        <span className="text-lg font-black text-brand-accent font-mono">₹{total.toLocaleString()}</span>
      </div>
    </div>
  );
};
