import React from 'react';
import { DollarSign, Truck, Train, Ship, Package } from 'lucide-react';

interface CostBreakdownTableProps {
  breakdown: Record<string, number>;
  total: number;
}

export const CostBreakdownTable: React.FC<CostBreakdownTableProps> = ({ breakdown, total }) => {
  const getIcon = (mode: string) => {
    const m = mode.toLowerCase();
    if (m === 'ocean') return <Ship size={14} />;
    if (m === 'rail') return <Train size={14} />;
    if (m === 'truck') return <Truck size={14} />;
    return <Package size={14} />;
  };

  const getLabel = (mode: string) => {
    if (mode === 'Handling') return 'Mode-Switch Fees';
    return `${mode} Freight`;
  };

  return (
    <div className="cost-breakdown-panel mt-4 p-4 bg-surface rounded-xl border border-subtle">
      <div className="flex items-center gap-2 mb-4">
        <DollarSign size={14} className="text-brand-primary" />
        <h4 className="text-[10px] font-black text-secondary uppercase tracking-widest">Executable Cost Matrix</h4>
      </div>

      <div className="space-y-3">
        {Object.entries(breakdown).map(([mode, cost], i) => (
          <div key={i} className="space-y-1.5">
            <div className="flex justify-between items-center text-[11px] font-bold">
              <div className="flex items-center gap-2 text-muted">
                {getIcon(mode)}
                <span>{getLabel(mode)}</span>
              </div>
              <span className="font-mono text-primary">${cost.toLocaleString()}</span>
            </div>
            <div className="h-1 bg-subtle rounded-full overflow-hidden">
              <div 
                className="h-full bg-brand-primary/40 transition-all duration-1000" 
                style={{ width: `${(cost / total) * 100}%` }}
              ></div>
            </div>
          </div>
        ))}
      </div>

      <div className="mt-4 pt-4 border-t border-subtle flex justify-between items-center">
        <span className="text-[10px] font-black text-muted uppercase tracking-widest">Total Executable Cost</span>
        <span className="text-sm font-black text-brand-primary font-mono">${total.toLocaleString()}</span>
      </div>
    </div>
  );
};
