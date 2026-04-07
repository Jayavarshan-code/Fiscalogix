import React from 'react';
import { Layers, Shield, Clock, TrendingUp, DollarSign } from 'lucide-react';

// Shape returned by scenario_engine.py
interface BackendScenario {
  scenario: string;
  shocks_applied: {
    delay_shift_days: number;
    demand_shift_pct: number;
    fx_shock_pct: number;
    cost_shock_pct: number;
    international_only: boolean;
  };
  impact: {
    revm_change: number;
    revm_change_pct: number;
    peak_deficit: number;
  };
}

interface ScenarioComparisonMatrixProps {
  scenarios?: BackendScenario[];
}

// Static fallback for when no backend data is available
const STATIC_SCENARIOS = [
  { name: 'Route A (Rail)',  cost: '$7.8k', risk: 'Low',  delay: 't+3d',  efi: '₹14.2k', isSafe: true },
  { name: 'Route B (Ocean)', cost: '$3.1k', risk: 'Med',  delay: 't+14d', efi: '₹9.8k'  },
  { name: 'Route C (Truck)', cost: '$5.2k', risk: 'High', delay: 't+1d',  efi: '-₹2.4k' },
];

const fmt = (n: number) =>
  `${n < 0 ? '-' : ''}₹${Math.abs(n).toLocaleString('en-IN', { maximumFractionDigits: 0 })}`;

export const ScenarioComparisonMatrix: React.FC<ScenarioComparisonMatrixProps> = ({ scenarios }) => {
  const hasLive = scenarios && scenarios.length > 0;

  return (
    <div className="mt-8 overflow-hidden rounded-2xl border border-subtle bg-surface shadow-2xl">
      <div className="flex items-center gap-2 p-4 bg-surface-elevated border-b border-subtle">
        <Layers size={14} className="text-brand-primary" />
        <h4 className="text-[10px] font-black text-secondary uppercase tracking-widest">
          {hasLive ? 'Stress-Test Scenario Battery (Live)' : 'Side-by-Side Scenario Matrix'}
        </h4>
      </div>

      <div className="overflow-x-auto">
        {hasLive ? (
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-surface text-[10px] font-black text-muted uppercase tracking-tighter">
                <th className="p-4 border-b border-subtle">Scenario</th>
                <th className="p-4 border-b border-subtle"><div className="flex items-center gap-1"><Clock size={10} /> Delay Shift</div></th>
                <th className="p-4 border-b border-subtle"><div className="flex items-center gap-1"><DollarSign size={10} /> FX Shock</div></th>
                <th className="p-4 border-b border-subtle"><div className="flex items-center gap-1"><TrendingUp size={10} /> ReVM Δ</div></th>
                <th className="p-4 border-b border-subtle"><div className="flex items-center gap-1"><Shield size={10} /> ReVM Δ%</div></th>
              </tr>
            </thead>
            <tbody>
              {scenarios!.map((s, i) => {
                const isPositive = s.impact.revm_change >= 0;
                return (
                  <tr key={i} className={`hover:bg-brand-primary/5 transition-all ${isPositive ? 'bg-safe/5' : ''}`}>
                    <td className="p-4 text-[11px] font-black text-primary border-b border-subtle">
                      <div className="flex items-center gap-2">
                        {isPositive && <div className="w-1.5 h-1.5 rounded-full bg-safe shadow-[0_0_8px_rgba(34,197,94,1)]" />}
                        {s.scenario}
                      </div>
                    </td>
                    <td className="p-4 text-[10px] font-mono text-secondary border-b border-subtle">
                      {s.shocks_applied.delay_shift_days > 0 ? `+${s.shocks_applied.delay_shift_days}d` : '—'}
                    </td>
                    <td className="p-4 text-[10px] font-mono border-b border-subtle">
                      {s.shocks_applied.fx_shock_pct !== 0
                        ? <span className={s.shocks_applied.fx_shock_pct > 0 ? 'text-critical' : 'text-safe'}>
                            {s.shocks_applied.fx_shock_pct > 0 ? '+' : ''}{(s.shocks_applied.fx_shock_pct * 100).toFixed(0)}%
                          </span>
                        : <span className="text-muted">—</span>}
                    </td>
                    <td className={`p-4 text-[11px] font-black border-b border-subtle ${isPositive ? 'text-safe' : 'text-critical'}`}>
                      {fmt(s.impact.revm_change)}
                    </td>
                    <td className={`p-4 text-[11px] font-black border-b border-subtle ${isPositive ? 'text-safe' : 'text-critical'}`}>
                      {s.impact.revm_change_pct > 0 ? '+' : ''}{s.impact.revm_change_pct.toFixed(1)}%
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        ) : (
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-surface text-[10px] font-black text-muted uppercase tracking-tighter">
                <th className="p-4 border-b border-subtle">Scenario</th>
                <th className="p-4 border-b border-subtle"><div className="flex items-center gap-1"><DollarSign size={10} /> Cost</div></th>
                <th className="p-4 border-b border-subtle"><div className="flex items-center gap-1"><Shield size={10} /> Risk</div></th>
                <th className="p-4 border-b border-subtle"><div className="flex items-center gap-1"><Clock size={10} /> Delay</div></th>
                <th className="p-4 border-b border-subtle"><div className="flex items-center gap-1"><TrendingUp size={10} /> EFI</div></th>
              </tr>
            </thead>
            <tbody>
              {STATIC_SCENARIOS.map((s, i) => (
                <tr key={i} className={`hover:bg-brand-primary/5 transition-all ${s.isSafe ? 'bg-safe/5' : ''}`}>
                  <td className="p-4 text-[11px] font-black text-primary border-b border-subtle">
                    <div className="flex items-center gap-2">
                      {s.isSafe && <div className="w-1.5 h-1.5 rounded-full bg-safe shadow-[0_0_8px_rgba(34,197,94,1)]" />}
                      {s.name}
                    </div>
                  </td>
                  <td className="p-4 text-[10px] font-mono text-secondary border-b border-subtle">{s.cost}</td>
                  <td className={`p-4 text-[10px] font-bold border-b border-subtle ${s.risk === 'Low' ? 'text-safe' : s.risk === 'High' ? 'text-critical' : 'text-warning'}`}>{s.risk}</td>
                  <td className="p-4 text-[10px] text-muted border-b border-subtle">{s.delay}</td>
                  <td className={`p-4 text-[11px] font-black border-b border-subtle ${s.efi.startsWith('-') ? 'text-critical' : 'text-safe'}`}>{s.efi}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
};
