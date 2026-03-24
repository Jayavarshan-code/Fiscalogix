import React from 'react';
import { Info, AlertTriangle } from 'lucide-react';

interface ConstraintVisibilityPanelProps {
  constraints: string[];
  capacityUtilization: number;
  costBudgetUtilization: number;
  slaHealth: number;
}

export const ConstraintVisibilityPanel: React.FC<ConstraintVisibilityPanelProps> = ({ 
  constraints, 
  capacityUtilization, 
  costBudgetUtilization,
  slaHealth
}) => {
  return (
    <div className="constraint-visibility-panel mt-6 p-4 bg-surface-elevated rounded-xl border border-subtle shadow-inner">
      <div className="flex items-center gap-2 mb-4">
        <Info size={14} className="text-brand-primary" />
        <h4 className="text-[10px] font-black text-secondary uppercase tracking-widest">Decision Logic (Tight Constraints)</h4>
      </div>

      <div className="space-y-4">
        {/* Progress Metrics */}
        <div className="grid grid-cols-1 gap-3">
          <div className="space-y-1">
             <div className="flex justify-between text-[9px] font-bold uppercase text-muted">
                <span>Network Capacity</span>
                <span className={capacityUtilization > 90 ? 'text-critical' : ''}>{capacityUtilization}%</span>
             </div>
             <div className="h-1 bg-subtle rounded-full overflow-hidden">
                <div className={`h-full transition-all duration-1000 ${capacityUtilization > 90 ? 'bg-critical' : 'bg-brand-primary'}`} style={{ width: `${capacityUtilization}%` }}></div>
             </div>
          </div>

          <div className="space-y-1">
             <div className="flex justify-between text-[9px] font-bold uppercase text-muted">
                <span>Budget Liquidity</span>
                <span>{costBudgetUtilization}%</span>
             </div>
             <div className="h-1 bg-subtle rounded-full overflow-hidden">
                <div className="h-full bg-secondary transition-all duration-1000" style={{ width: `${costBudgetUtilization}%` }}></div>
             </div>
          </div>
          
          <div className="space-y-1">
             <div className="flex justify-between text-[9px] font-bold uppercase text-muted">
                <span>SLA Integrity</span>
                <span className="text-safe">{slaHealth}%</span>
             </div>
             <div className="h-1 bg-subtle rounded-full overflow-hidden">
                <div className="h-full bg-safe transition-all duration-1000" style={{ width: `${slaHealth}%` }}></div>
             </div>
          </div>
        </div>

        {/* Narrative Constraint Log */}
        {constraints && constraints.length > 0 && (
          <div className="mt-4 p-3 bg-critical/5 border border-critical/10 rounded-lg">
            {constraints.map((msg, i) => (
              <div key={i} className="flex gap-2 items-start text-[10px] text-critical leading-tight">
                <AlertTriangle size={12} className="shrink-0 mt-0.5" />
                <p>{msg}</p>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
