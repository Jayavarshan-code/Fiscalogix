import React from 'react';
import { CheckCircle, TrendingUp, ShieldCheck, AlertTriangle } from 'lucide-react';

interface ExecutiveDecisionBannerProps {
  action: string;
  profitImpact: string;
  riskReduction: string;
  isCritical?: boolean;
}

export const ExecutiveDecisionBanner: React.FC<ExecutiveDecisionBannerProps> = ({ 
  action, 
  profitImpact, 
  riskReduction, 
  isCritical = false 
}) => {
  return (
    <div className="space-y-3 mb-6">
      {isCritical && (
        <div className="flex items-center gap-2 p-3 bg-critical/10 border border-critical rounded-xl animate-pulse">
          <AlertTriangle className="text-critical" size={18} />
          <span className="text-[11px] font-black text-critical uppercase tracking-widest">
            Critical Disruption Detected: Immediate Action Required
          </span>
        </div>
      )}
      
      <div className="flex flex-col gap-4 p-5 bg-surface-elevated border border-brand-primary/30 rounded-2xl shadow-xl glassmorphism">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-safe/20 rounded-full">
            <CheckCircle className="text-safe" size={24} />
          </div>
          <div>
            <h3 className="text-[10px] font-black text-muted uppercase tracking-widest">Recommended Strategic Action</h3>
            <p className="text-lg font-black text-primary tracking-tight">{action}</p>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4 pt-4 border-t border-subtle">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-brand-primary/10 rounded-lg">
              <TrendingUp className="text-brand-primary" size={18} />
            </div>
            <div>
              <span className="block text-[9px] font-bold text-muted uppercase">EFI Strategy Delta</span>
              <span className="text-sm font-black text-safe">{profitImpact.startsWith('-') ? '' : '+'}₹{(parseInt(profitImpact.replace(/[^0-9-]/g, '')) || 0).toLocaleString()}</span>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <div className="p-2 bg-safe/10 rounded-lg">
              <ShieldCheck className="text-safe" size={18} />
            </div>
            <div>
              <span className="block text-[9px] font-bold text-muted uppercase">Risk Reduction</span>
              <span className="text-sm font-black text-brand-primary">{riskReduction}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
