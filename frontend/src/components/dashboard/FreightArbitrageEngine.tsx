import React, { useState } from 'react';
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
}

const FreightArbitrageEngine: React.FC<FreightArbitrageEngineProps> = ({
  headline,
  breakdown,
  recommended_action,
  roi_improvement,
  new_loss
}) => {
  const [isExpanded, setIsExpanded] = useState(true);

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
              <span className="roi-tag">🚀 {roi_improvement} Capital Recouped</span>
            </div>
            <p className="description">{recommended_action}</p>
            <div className="decision-footer">
              <span className="new-loss">Projected Loss: ₹{new_loss}</span>
              <button className="execute-btn shrink-to-fit">Execute Hedging Strategy</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default FreightArbitrageEngine;
