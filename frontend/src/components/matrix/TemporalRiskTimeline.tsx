import React from 'react';
import { Clock, CloudRain, Ship, MessageSquare, AlertTriangle } from 'lucide-react';

interface RiskMarker {
  time_hours: number;
  score: number;
  label: string;
  signals?: { type: string; message: string }[];
  bands?: [number, number, number]; // [Best, Expected, Worst]
}

interface TemporalRiskTimelineProps {
  markers: RiskMarker[];
}

export const TemporalRiskTimeline: React.FC<TemporalRiskTimelineProps> = ({ markers }) => {
  if (!markers || markers.length === 0) return null;

  const horizon = 72;
  const getPosition = (h: number) => (h / horizon) * 100;

  const getSignalIcon = (type: string) => {
    switch (type) {
      case 'WEATHER': return <CloudRain size={14} className="text-blue-400" />;
      case 'AIS': return <Ship size={14} className="text-brand-secondary" />;
      case 'NEWS': return <MessageSquare size={14} className="text-amber-400" />;
      default: return <AlertTriangle size={14} className="text-critical" />;
    }
  };

  return (
    <div className="temporal-timeline-container mt-6 bg-surface p-4 rounded-xl border border-subtle shadow-sm">
      <div className="flex justify-between items-center mb-6">
        <div>
           <h4 className="text-sm font-bold text-secondary uppercase tracking-tight">Predictive Risk Radar</h4>
           <p className="text-[10px] text-muted font-medium italic">Multimodal Contagion & Probabilistic Horizon</p>
        </div>
        <div className="flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-surface-elevated border border-subtle">
           <Clock size={12} className="text-brand-primary" />
           <span className="text-[10px] font-bold text-secondary uppercase tracking-wider">72h Horizon</span>
        </div>
      </div>

      <div className="relative pt-12 pb-4 px-2">
        {/* Confidence Band Shaded Area (SVG Path) */}
        <svg className="absolute inset-0 w-full h-full pointer-events-none opacity-[0.07]" style={{ padding: '0 1rem' }}>
          <path 
            d={`M ${markers.map(m => `${getPosition(m.time_hours)}% ${50 - (m.bands?.[2] || m.score) * 40}`).join(' L ')} 
               L ${[...markers].reverse().map(m => `${getPosition(m.time_hours)}% ${50 - (m.bands?.[0] || m.score * 0.5) * 40}`).join(' L ')} Z`}
            fill="var(--brand-primary)"
          />
        </svg>

        {/* Main Timeline Line */}
        <div className="absolute top-1/2 left-0 right-0 h-[3px] bg-subtle transform -translate-y-1/2 rounded-full shadow-inner opacity-40"></div>
        
        {/* Risk Markers */}
        <div className="relative h-20 w-full flex items-center">
          {markers.map((m, i) => {
            const pos = getPosition(m.time_hours);
            const level = m.score > 0.8 ? 'critical' : m.score > 0.4 ? 'medium' : 'safe';
            
            return (
              <div 
                key={i} 
                className="absolute flex flex-col items-center group cursor-help"
                style={{ left: `${pos}%`, transform: 'translateX(-50%)' }}
              >
                {/* Score Bubble and Indicators */}
                <div className="absolute bottom-12 flex flex-col items-center gap-2">
                    <div className="flex gap-1">
                      {m.signals?.slice(0, 3).map((sig, idx) => (
                        <div key={idx} className="p-1.5 rounded-lg bg-surface-elevated border border-subtle shadow-md transition-transform group-hover:scale-110">
                           {getSignalIcon(sig.type)}
                        </div>
                      ))}
                    </div>
                </div>

                {/* Score Point */}
                <div className={`
                    w-4 h-4 rounded-full flex items-center justify-center 
                    border-4 transition-all duration-300 group-hover:scale-125 z-10
                    ${level === 'critical' ? 'bg-critical border-critical-subtle' : 
                      level === 'medium' ? 'bg-warning border-warning-subtle' : 
                      'bg-safe border-safe-subtle'}
                `}></div>

                {/* Node Label */}
                <div className="mt-3 text-[10px] font-bold text-secondary whitespace-nowrap bg-surface-elevated px-2 py-1 rounded-lg shadow-sm border border-subtle">
                   {m.label} <span className="text-muted font-mono ml-1">T+{m.time_hours}h</span>
                </div>

                {/* Technical Tooltip */}
                <div className="absolute -top-20 opacity-0 group-hover:opacity-100 transition-all transform group-hover:-translate-y-2 p-3 rounded-xl shadow-2xl z-30 w-48 pointer-events-none" style={{ background: 'var(--bg-surface-elevated)', border: '1px solid var(--border-strong)', color: 'var(--text-primary)' }}>
                    <div className="flex justify-between items-center mb-2 border-b border-white/10 pb-1">
                        <span className="text-[9px] font-black uppercase tracking-widest text-slate-400">Risk Advisor</span>
                        <span className="text-[12px] font-mono font-bold text-brand-primary">{(m.score * 100).toFixed(0)}%</span>
                    </div>
                    <div className="space-y-1.5">
                       {m.bands && (
                         <div className="flex justify-between text-[9px] font-mono">
                            <span className="text-green-400">Best: {(m.bands[0]*100).toFixed(0)}%</span>
                            <span className="text-red-400">Worst: {(m.bands[2]*100).toFixed(0)}%</span>
                         </div>
                       )}
                       {m.signals?.map((sig, idx) => (
                         <p key={idx} className="text-[10px] leading-tight flex gap-1.5 items-start">
                             <span className="mt-0.5">•</span>
                             {sig.message}
                         </p>
                       ))}
                    </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
      
      <div className="flex justify-between mt-4 px-2">
        <div className="flex items-center gap-1.5">
           <div className="w-1.5 h-1.5 rounded-full bg-brand-primary pulse"></div>
           <span className="text-[10px] font-black text-brand-primary uppercase tracking-widest">Live Signals</span>
        </div>
        <span className="text-[9px] font-bold text-muted uppercase tracking-widest text-right">Horizon: 72 Hours Out</span>
      </div>
    </div>
  );
};
