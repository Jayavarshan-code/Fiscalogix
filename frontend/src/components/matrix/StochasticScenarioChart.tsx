import React from 'react';

interface StochasticScenarioChartProps {
  scenarios: number[];
  cvarFloor: number;
}

export const StochasticScenarioChart: React.FC<StochasticScenarioChartProps> = ({ scenarios, cvarFloor }) => {
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
      <div className="flex justify-between items-center mb-2">
        <h4 className="text-sm font-semibold text-secondary uppercase tracking-tight">Scenario Distribution (ReVM)</h4>
        <span className="text-xs font-medium text-brand-primary">n=200 parallel futures</span>
      </div>
      
      <div className="relative h-24 w-full flex items-end gap-1 px-1">
        {/* CVaR Floor Marker */}
        <div 
          className="absolute h-full border-l-2 border-dashed border-critical z-10" 
          style={{ left: `${floorThresholdPercent}%`, opacity: 0.6 }}
        >
          <div className="absolute -top-6 -left-12 bg-surface text-critical text-[10px] font-bold px-1.5 py-0.5 rounded border border-critical">
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
                    className={`flex-grow rounded-t-sm transition-all duration-500`}
                    style={{ 
                        height: `${height}%`, 
                        backgroundColor: isAtRisk ? 'rgba(239, 68, 68, 0.4)' : 'rgba(37, 99, 235, 0.4)',
                        border: `1px solid ${isAtRisk ? 'rgba(239, 68, 68, 0.2)' : 'rgba(37, 99, 235, 0.2)'}`
                    }}
                    title={`Value: $${bucketVal.toFixed(0)} - Count: ${count}`}
                />
            );
        })}
      </div>
      
      <div className="flex justify-between mt-1 text-[10px] text-muted font-medium">
        <span>Min: ${min.toLocaleString()}</span>
        <span>Max: ${max.toLocaleString()}</span>
      </div>
      
      <div className="mt-3 p-2 bg-surface-elevated rounded border border-subtle text-[11px] leading-tight">
        <strong className="text-brand-primary">Stochastic Insight:</strong> Even in the worst 10% of market scenarios, 
        this action maintains a value of <strong>${cvarFloor.toLocaleString()}</strong>.
      </div>
    </div>
  );
};
