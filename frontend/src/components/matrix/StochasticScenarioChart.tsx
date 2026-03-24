import React from 'react';

interface StochasticScenarioChartProps {
  scenarios: number[];
  cvarFloor: number;
  narratives?: string[];
}

export const StochasticScenarioChart: React.FC<StochasticScenarioChartProps> = ({ scenarios, cvarFloor, narratives }) => {
  if (!scenarios || scenarios.length === 0) return null;

  const min = Math.min(...scenarios);
  const max = Math.max(...scenarios);
  const range = max - min;
  
  // Calculate distribution histogram buckets
  const bucketCount = 20;
  const buckets = new Array(bucketCount).fill(0);
  scenarios.forEach(s => {
    const bucketIdx = Math.min(bucketCount - 1, Math.floor(((s - min) / range) * bucketCount));
    buckets[bucketIdx]++;
  });
  
  const maxBucket = Math.max(...buckets);
  const floorThresholdPercent = ((cvarFloor - min) / range) * 100;

  return (
    <div className="stochastic-chart-container mt-4">
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-[10px] font-black text-secondary uppercase tracking-widest">Stochastic Simulation (n=200)</h3>
        <div className="px-2 py-0.5 rounded bg-surface border border-subtle">
           <span className="text-[9px] font-bold text-brand-primary">CVaR(0.1) ACTIVE</span>
        </div>
      </div>
      
      <div className="relative h-28 w-full flex items-end gap-1 px-1 mb-6">
        {/* CVaR Floor Marker */}
        <div 
          className="absolute h-full border-l-2 border-dashed border-critical z-20" 
          style={{ left: `${floorThresholdPercent}%`, opacity: 0.8 }}
        >
          <div className="absolute -top-8 -left-12 bg-surface text-critical text-[10px] font-black px-2 py-1 rounded-lg border border-critical shadow-lg whitespace-nowrap">
            ROBUST FLOOR: ${cvarFloor.toLocaleString()}
          </div>
        </div>

        {/* Distribution Bars */}
        {buckets.map((count, i) => {
            const height = (count / maxBucket) * 100;
            const bucketVal = min + (i * (range / bucketCount));
            const isAtRisk = bucketVal < cvarFloor;
            
            return (
                <div 
                    key={i} 
                    className="flex-grow rounded-t-sm transition-all duration-700 ease-out"
                    style={{ 
                        height: `${height}%`, 
                        backgroundColor: isAtRisk ? 'rgba(239, 68, 68, 0.5)' : 'rgba(37, 99, 235, 0.5)',
                        border: `1px solid ${isAtRisk ? 'rgba(239, 68, 68, 0.2)' : 'rgba(37, 99, 235, 0.2)'}`
                    }}
                />
            );
        })}
      </div>

      {/* Scenario Narratives Section */}
      <div className="mt-4 border-t border-subtle pt-4">
        <h4 className="text-[9px] font-black text-muted uppercase tracking-widest mb-3">Scenario Narratives</h4>
        <div className="space-y-2">
          {narratives?.map((story, idx) => {
            const isWorst = story.toLowerCase().includes('worst case');
            const isBest = story.toLowerCase().includes('best case');
            const isStrategy = story.toLowerCase().includes('strategy');

            return (
              <div 
                key={idx} 
                className={`
                  p-2.5 rounded-xl border leading-relaxed text-[11px] flex gap-3
                  ${isWorst ? 'bg-critical-subtle border-critical/20 text-critical shadow-sm' : 
                    isBest ? 'bg-safe-subtle border-safe/20 text-safe shadow-sm' : 
                    isStrategy ? 'bg-brand-primary/5 border-brand-primary/20 text-brand-primary shadow-sm' :
                    'bg-surface-elevated border-subtle text-secondary shadow-inner font-medium'}
                `}
              >
                <div className="mt-0.5 shrink-0">
                   {isWorst ? '🔴' : isBest ? '🟢' : isStrategy ? '🎯' : '👉'}
                </div>
                <p>{story}</p>
              </div>
            );
          }) || (
            <div className="p-3 bg-surface-elevated rounded-xl border border-subtle text-[11px] italic text-muted">
               Calculation engine idle. No probabilistic narratives available for this action branch.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
