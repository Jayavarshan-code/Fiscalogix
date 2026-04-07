import React, { useState } from 'react';
import { Loader2, CheckCircle } from 'lucide-react';
import { apiService } from '../../services/api';
import './FreightArbitrageEngine.css';

interface EFIBreakdown {
  delay_cost: number;
  penalty: number;
  inventory_cost: number;
  opportunity_cost: number;
}

interface FreightArbitrageEngineProps {
  headline: string;
  breakdown: EFIBreakdown;
  recommended_action: string;
  roi_improvement: string;
  new_loss: string;
  // Optional: if the calling context has route data, pass it in for a real hedge call
  routeContext?: { route_id: string; spot_rate: number; contract_rate: number };
}

const FreightArbitrageEngine: React.FC<FreightArbitrageEngineProps> = ({
  headline,
  breakdown,
  recommended_action,
  roi_improvement,
  new_loss,
  routeContext,
}) => {
  const [isExpanded, setIsExpanded] = useState(true);
  const [isExecuting, setIsExecuting] = useState(false);
  const [hedgeResult, setHedgeResult] = useState<any>(null);
  const [hedgeError, setHedgeError] = useState('');

  const handleExecuteHedge = async () => {
    setIsExecuting(true);
    setHedgeError('');
    try {
      // Use passed routeContext if available, else derive a representative payload
      const routes = [
        {
          route_id:              routeContext?.route_id            ?? 'DEFAULT_ROUTE',
          current_spot_rate:     routeContext?.spot_rate           ?? (breakdown.delay_cost + breakdown.inventory_cost),
          current_contract_rate: routeContext?.contract_rate       ?? (breakdown.penalty + breakdown.opportunity_cost),
          market_volatility_index: 1.15,
        },
      ];
      const results = await apiService.getFreightHedging(routes);
      setHedgeResult(results[0]);
    } catch (err: any) {
      setHedgeError(err.message || 'Hedging engine unavailable.');
      console.error('Freight hedging failed:', err);
    } finally {
      setIsExecuting(false);
    }
  };

  return (
    <div className={`copilot-container premium-card glass-panel ${isExpanded ? 'expanded' : 'collapsed'}`}>
      <div className="copilot-header" onClick={() => setIsExpanded(!isExpanded)}>
        <div className="headline-icon">🧠</div>
        <h2 className="efi-headline">{headline}</h2>
        <span className="expand-toggle">{isExpanded ? '−' : '+'}</span>
      </div>

      {isExpanded && (
        <div className="copilot-body animate-in">
          <div className="breakdown-section">
            <h4 className="section-title">Cost Breakdown (Financial Arbitrage)</h4>
            <div className="breakdown-grid">
              <div className="breakdown-item">
                <span className="label">Delay cost</span>
                <span className="value">₹{breakdown.delay_cost.toLocaleString()}</span>
              </div>
              <div className="breakdown-item">
                <span className="label">Penalty</span>
                <span className="value">₹{breakdown.penalty.toLocaleString()}</span>
              </div>
              <div className="breakdown-item">
                <span className="label">Inventory cost</span>
                <span className="value">₹{breakdown.inventory_cost.toLocaleString()}</span>
              </div>
              <div className="breakdown-item">
                <span className="label">Opportunity cost</span>
                <span className="value">₹{breakdown.opportunity_cost.toLocaleString()}</span>
              </div>
            </div>
          </div>

          <div className="decision-layer glass-panel">
            <div className="decision-header">
              <span className="action-badge">RECOMMENDED REROUTE</span>
              {roi_improvement && <span className="roi-tag">🚀 {roi_improvement} Capital Recouped</span>}
            </div>
            <p className="description">{recommended_action}</p>
            {new_loss && (
              <div className="decision-footer">
                <span className="new-loss">Projected Loss: ₹{new_loss}</span>
              </div>
            )}

            {/* Live hedging result */}
            {hedgeResult ? (
              <div className="mt-4 p-4 bg-safe/10 border border-safe/30 rounded-xl space-y-1">
                <div className="flex items-center gap-2 text-safe mb-2">
                  <CheckCircle size={16} />
                  <span className="text-[11px] font-black uppercase">Hedge Strategy Confirmed</span>
                </div>
                <div className="text-[10px] text-secondary space-y-1">
                  <div>Decision: <strong className="text-primary">{hedgeResult.arbitrage_decision}</strong></div>
                  <div>Predicted Spot Rate (6mo): <strong>${hedgeResult.predicted_spot_rate_6mo?.toLocaleString()}</strong></div>
                  <div>Est. Savings/FEU: <strong className="text-safe">${hedgeResult.expected_savings_per_feu?.toLocaleString()}</strong></div>
                  <div>Confidence: <strong>{(hedgeResult.decision_confidence * 100).toFixed(1)}%</strong></div>
                </div>
              </div>
            ) : hedgeError ? (
              <div className="mt-4 p-3 bg-critical/10 border border-critical/30 rounded-xl text-[10px] text-critical font-medium">
                {hedgeError}
              </div>
            ) : (
              <button
                className="execute-btn shrink-to-fit mt-4"
                onClick={handleExecuteHedge}
                disabled={isExecuting}
                style={{ display: 'flex', alignItems: 'center', gap: '8px', justifyContent: 'center' }}
              >
                {isExecuting
                  ? <><Loader2 size={14} className="animate-spin" /> Analysing Market Rates...</>
                  : 'Execute Hedging Strategy'}
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default FreightArbitrageEngine;
