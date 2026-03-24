import { Clock } from 'lucide-react';

interface RiskMarker {
  time_hours: number;
  score: number;
  label: string;
}

interface TemporalRiskTimelineProps {
  markers: RiskMarker[];
}

export const TemporalRiskTimeline: React.FC<TemporalRiskTimelineProps> = ({ markers }) => {
  if (!markers || markers.length === 0) return null;

  // Assume horizon is 72h
  const horizon = 72;
  
  const getPosition = (h: number) => (h / horizon) * 100;

  return (
    <div className="temporal-timeline-container mt-6">
      <div className="flex justify-between items-center mb-4">
        <h4 className="text-sm font-semibold text-secondary uppercase tracking-tight">Temporal Risk Contagion</h4>
        <div className="flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-surface-elevated border border-subtle">
           <Clock size={12} className="text-brand-primary" />
           <span className="text-[10px] font-bold text-secondary uppercase tracking-wider">72h Propagation Horizon</span>
        </div>
      </div>

      <div className="relative pt-6 pb-2">
        {/* Main Timeline Line */}
        <div className="absolute top-1/2 left-0 right-0 h-[2px] bg-subtle transform -translate-y-1/2 rounded-full overflow-hidden">
             <div className="h-full bg-brand-primary" style={{ width: '10%' }}></div> {/* Gradient from NOW */}
        </div>
        
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
                {/* Score Bubble */}
                <div className={`
                    absolute bottom-10 w-10 h-10 rounded-full flex items-center justify-center 
                    border-2 transition-all duration-300 group-hover:scale-110
                    ${level === 'critical' ? 'bg-critical-subtle border-critical text-critical' : 
                      level === 'medium' ? 'bg-warning-subtle border-warning text-warning' : 
                      'bg-safe-subtle border-safe text-safe'}
                `}>
                  <span className="text-[11px] font-bold">{(m.score * 100).toFixed(0)}%</span>
                </div>

                {/* Vertical Connector */}
                <div className={`w-[2px] h-6 ${level === 'critical' ? 'bg-critical' : level === 'medium' ? 'bg-warning' : 'bg-safe'} opacity-40`} />
                
                {/* Node Label */}
                <div className="mt-2 text-[10px] font-semibold text-secondary whitespace-nowrap bg-surface-elevated px-1.5 py-0.5 rounded shadow-sm border border-subtle">
                   {m.label} (T+{m.time_hours}h)
                </div>

                {/* Tooltip detail */}
                <div className="absolute -top-16 opacity-0 group-hover:opacity-100 transition-opacity bg-surface p-2 rounded shadow-xl border border-subtle z-20 w-32 pointer-events-none">
                    <p className="text-[9px] font-bold uppercase text-muted mb-1">Contagion Snapshot</p>
                    <p className="text-[10px] text-primary leading-tight">Predicted shock arrival at {m.time_hours} hours offset from origin.</p>
                </div>
              </div>
            );
          })}
        </div>
      </div>
      
      <div className="flex justify-between mt-2 px-1">
        <span className="text-[9px] font-black text-brand-primary uppercase tracking-widest">Now</span>
        <span className="text-[9px] font-black text-muted uppercase tracking-widest text-right">Horizon (72h)</span>
      </div>
    </div>
  );
};
