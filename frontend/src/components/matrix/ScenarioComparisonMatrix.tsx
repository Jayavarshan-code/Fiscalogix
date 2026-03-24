import React from 'react';
import { Layers, Shield, Clock, TrendingUp, DollarSign } from 'lucide-react';

interface ScenarioData {
  name: string;
  cost: string;
  risk: string;
  delay: string;
  efi: string;
  isSafe?: boolean;
}

export const ScenarioComparisonMatrix: React.FC = () => {
  const scenarios: ScenarioData[] = [
    { name: 'Route A (Rail)', cost: '$7.8k', risk: 'Low', delay: 't+3d', efi: '₹14.2k', isSafe: true },
    { name: 'Route B (Ocean)', cost: '$3.1k', risk: 'Med', delay: 't+14d', efi: '₹9.8k' },
    { name: 'Route C (Truck)', cost: '$5.2k', risk: 'High', delay: 't+1d', efi: '-₹2.4k' },
  ];

  return (
    <div className="mt-8 overflow-hidden rounded-2xl border border-subtle bg-surface shadow-2xl">
      <div className="flex items-center gap-2 p-4 bg-surface-elevated border-b border-subtle">
        <Layers size={14} className="text-brand-primary" />
        <h4 className="text-[10px] font-black text-secondary uppercase tracking-widest">Side-by-Side Scenario Matrix</h4>
      </div>
      
      <div className="overflow-x-auto">
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
            {scenarios.map((s, i) => (
              <tr key={i} className={`hover:bg-brand-primary/5 transition-all ${s.isSafe ? 'bg-safe/5' : ''}`}>
                <td className="p-4 text-[11px] font-black text-primary border-b border-subtle">
                  <div className="flex items-center gap-2">
                    {s.isSafe && <div className="w-1.5 h-1.5 rounded-full bg-safe shadow-[0_0_8px_rgba(34,197,94,1)]" />}
                    {s.name}
                  </div>
                </td>
                <td className="p-4 text-[10px] font-mono text-secondary border-b border-subtle">{s.cost}</td>
                <td className={`p-4 text-[10px] font-bold border-b border-subtle ${s.risk === 'Low' ? 'text-safe' : s.risk === 'High' ? 'text-critical' : 'text-warning'}`}>
                  {s.risk}
                </td>
                <td className="p-4 text-[10px] text-muted border-b border-subtle">{s.delay}</td>
                <td className={`p-4 text-[11px] font-black border-b border-subtle ${s.efi.startsWith('-') ? 'text-critical' : 'text-safe'}`}>
                  {s.efi}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};
