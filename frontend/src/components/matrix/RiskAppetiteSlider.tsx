import React from 'react';
import { ShieldCheck, Scale, Zap } from 'lucide-react';

export type RiskAppetite = 'CONSERVATIVE' | 'BALANCED' | 'AGGRESSIVE';

interface RiskAppetiteSliderProps {
  value: RiskAppetite;
  onChange: (value: RiskAppetite) => void;
}

export const RiskAppetiteSlider: React.FC<RiskAppetiteSliderProps> = ({ value, onChange }) => {
  const options = [
    { 
      id: 'CONSERVATIVE' as RiskAppetite, 
      label: 'Conservative', 
      icon: <ShieldCheck size={14} />, 
      desc: 'Maximize Safety Floor (CVaR 0.05)',
      color: 'text-safe'
    },
    { 
      id: 'BALANCED' as RiskAppetite, 
      label: 'Balanced', 
      icon: <Scale size={14} />, 
      desc: 'Optimal Risk/Reward (CVaR 0.15)',
      color: 'text-brand-primary'
    },
    { 
      id: 'AGGRESSIVE' as RiskAppetite, 
      label: 'Aggressive', 
      icon: <Zap size={14} />, 
      desc: 'Maximize Expected Profit (CVaR 0.35)',
      color: 'text-warning'
    }
  ];

  return (
    <div className="risk-appetite-selector mt-6">
      <h4 className="text-[10px] font-black text-muted uppercase tracking-widest mb-3">Adjustable Risk Appetite</h4>
      
      <div className="flex gap-2">
        {options.map((opt) => {
          const isActive = value === opt.id;
          return (
            <button
              key={opt.id}
              onClick={() => onChange(opt.id)}
              className={`
                flex-1 flex flex-col items-center gap-1.5 p-3 rounded-xl border transition-all duration-300
                ${isActive ? `bg-surface border-brand-primary shadow-lg scale-105 z-10` : 'bg-surface-elevated border-subtle opacity-60 grayscale hover:grayscale-0'}
              `}
            >
              <div className={`${isActive ? opt.color : 'text-muted'}`}>
                {opt.icon}
              </div>
              <span className={`text-[10px] font-bold ${isActive ? 'text-primary' : 'text-muted'}`}>
                {opt.label}
              </span>
            </button>
          );
        })}
      </div>
      
      <div className="mt-3 text-center">
        <p className="text-[10px] text-brand-primary font-medium italic">
          {options.find(o => o.id === value)?.desc}
        </p>
      </div>
    </div>
  );
};
