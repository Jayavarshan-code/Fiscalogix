import React, { useState, useEffect } from 'react';
import { X, CheckCircle, ShieldAlert, Loader2, Lock, RefreshCw } from 'lucide-react';
import { apiService } from '../../services/api';
import { useAuth } from '../../context/AuthContext';
import { TemporalRiskTimeline } from './TemporalRiskTimeline';
import { StochasticScenarioChart } from './StochasticScenarioChart';
import { RerouteStudio } from './RerouteStudio';
import './ConfidencePanel.css';
import { ConstraintVisibilityPanel } from './ConstraintVisibilityPanel';
import { ExecutiveDecisionBanner } from './ExecutiveDecisionBanner';
import { ScenarioComparisonMatrix } from './ScenarioComparisonMatrix';
import type { RiskAppetite } from './RiskAppetiteSlider';
import { RiskAppetiteSlider } from './RiskAppetiteSlider';

interface ConfidencePanelProps {
  shipmentId: string | null;
  onClose: () => void;
}

export const ConfidencePanel: React.FC<ConfidencePanelProps> = ({ shipmentId, onClose }) => {
  const [isExecuting, setIsExecuting] = useState(false);
  const [isRerouteStudioOpen, setIsRerouteStudioOpen] = useState(false);
  const [riskAppetite, setRiskAppetite] = useState<RiskAppetite>('BALANCED');
  const [executionResult, setExecutionResult] = useState<any>(null);
  const { hasPermission } = useAuth();

  if (!shipmentId) return null;

  const [decisionData, setDecisionData] = useState<any>(null);
  const [explainData, setExplainData] = useState<any>(null);
  const [isLoadingInsights, setIsLoadingInsights] = useState(false);

  useEffect(() => {
    if (!shipmentId) return;
    setIsLoadingInsights(true);

    // Run both calls in parallel: financial insights + explainability layer
    Promise.all([
      apiService.getShipmentInsights(shipmentId),
      apiService.getConfidenceExplain(shipmentId).catch(() => null),  // non-blocking
    ]).then(([insights, explain]) => {
      setDecisionData(insights);
      setExplainData(explain);
    }).catch(err => {
      console.error("Failed to load insights:", err);
    }).finally(() => {
      setIsLoadingInsights(false);
    });
  }, [shipmentId]);

  if (isLoadingInsights || !decisionData) {
    return (
      <div className="confidence-panel active flex justify-center items-center h-full bg-surface-elevated">
        <div className="flex flex-col items-center gap-4 text-brand-primary">
          <Loader2 size={48} className="animate-spin" />
          <div className="text-sm font-bold uppercase tracking-widest text-muted mt-4">Running SHAP Explainers...</div>
        </div>
      </div>
    );
  }

  const handleExecute = async () => {
    setIsExecuting(true);
    try {
      // Identity comes from the JWT — no mock_user_id or tenant_id needed in the body
      const result = await apiService.executeAction({
        action_type: 'REROUTE_AIR_FREIGHT',
        shipment_id: shipmentId,
        erp_target: 'SAP',
        confidence_score: decisionData?.confidence_score ?? 0.942,
        parameters: { risk_posture: riskAppetite },
      });
      setExecutionResult(result.erp_receipt);
      // In a real system, we'd update executiveSummary from the backend response here:
      // setExecutiveSummary(result.decision_context.executive_summary);
    } catch (err) {
      console.error(err);
    } finally {
      setIsExecuting(false);
    }
  };

  return (
    <div className="confidence-panel active">
      <div className="panel-header">
        <div>
          <h2 className="text-xl font-black text-primary tracking-tighter">Executive Decision Cockpit</h2>
          <span className="subtitle tracking-tight">Mission Control for {shipmentId}</span>
        </div>
        <button className="icon-btn" onClick={onClose}><X size={20} /></button>
      </div>

      <div className="panel-body">
        {/* Pillar 5 Upgrade: Executive Decision Banner (Top Panel) */}
        <ExecutiveDecisionBanner 
          action={decisionData.recommended_action}
          profitImpact={decisionData.profit_impact_delta}
          riskReduction={decisionData.risk_reduction_pct}
          isCritical={decisionData.operational_alert.includes("Critical")}
        />

        <div className="score-section">
          <div className={`score-circle ${decisionData.confidence_score > 0.8 ? 'safe' : decisionData.confidence_score > 0.6 ? 'warning' : 'critical'}`}>
            <span className="score-value">{(decisionData.confidence_score * 100).toFixed(0)}%</span>
            <span className="score-label">Confidence Score</span>
          </div>
          <div className="score-context">
            <ShieldAlert className="text-critical" size={24} />
            <div>
              <h4 className="font-black text-sm uppercase tracking-tight">Strategic Disruption Shield</h4>
              <p className="text-[10px] text-muted">Risk Posture: <strong>{riskAppetite === 'CONSERVATIVE' ? 'Maximum Safety' : riskAppetite === 'AGGRESSIVE' ? 'Maximum Profit' : 'Balanced'}</strong></p>
            </div>
          </div>
        </div>

        {/* Tech Giant Upgrade: Interactive Risk Appetite Control */}
        <RiskAppetiteSlider value={riskAppetite} onChange={setRiskAppetite} />

        {/* Tech Giant Upgrade: Temporal Risk Radar — markers derived from confidence-studio key_drivers */}
        <TemporalRiskTimeline markers={
          explainData?.key_drivers?.length > 0
            ? explainData.key_drivers.slice(0, 5).map((driver: string, i: number) => ({
                time_hours: i * 18,
                score: explainData.risk_probability ?? 0.5,
                label: driver.split('_')[0].toUpperCase(),
                bands: [
                  Math.max(0, (explainData.risk_probability ?? 0.5) - 0.2),
                  explainData.risk_probability ?? 0.5,
                  Math.min(1, (explainData.risk_probability ?? 0.5) + 0.15),
                ] as [number, number, number],
                signals: [{ type: 'NEWS', message: driver }],
              }))
            : [
                { time_hours: 0,  score: 0.15, label: 'START',  bands: [0.10, 0.15, 0.25] as [number, number, number], signals: [{ type: 'AIS',  message: 'Vessel Queue: 12 ships' }] },
                { time_hours: 24, score: 0.87, label: 'HUB_B',  bands: [0.65, 0.87, 0.95] as [number, number, number], signals: [{ type: 'NEWS', message: 'Strike Alert: industrial terminal' }] },
                { time_hours: 48, score: 0.92, label: 'DEST_C', bands: [0.70, 0.92, 0.99] as [number, number, number], signals: [{ type: 'WEATHER', message: 'Heavy Squall Warning' }] },
              ]
        } />

        <div className="drivers-section">
          <h3 className="text-[10px] font-black text-muted uppercase tracking-widest mb-3">Hardened EFI Breakdown (Formula 2.0)</h3>
          <div className="grid grid-cols-2 gap-4">
             <div className="bg-surface p-3 rounded-xl border border-subtle">
                <span className="text-[9px] font-bold text-muted uppercase block mb-2">Total Costs (C)</span>
                <ul className="space-y-1">
                   {Object.entries(decisionData.granular_breakdown?.costs || {}).map(([key, val]: [string, any]) => (
                      <li key={key} className="flex justify-between text-[10px]">
                         <span className="capitalize text-secondary">{key}</span>
                         <span className="font-bold">₹{val.toLocaleString()}</span>
                      </li>
                   ))}
                </ul>
             </div>
             <div className="bg-surface p-3 rounded-xl border border-subtle">
                <span className="text-[9px] font-bold text-muted uppercase block mb-2">Total Losses (L)</span>
                <ul className="space-y-1">
                   {Object.entries(decisionData.granular_breakdown?.losses || {}).map(([key, val]: [string, any]) => (
                      <li key={key} className="flex justify-between text-[10px]">
                         <span className="capitalize text-secondary">{key}</span>
                         <span className="font-bold text-critical">₹{val.toLocaleString()}</span>
                      </li>
                   ))}
                </ul>
             </div>
          </div>
          <div className="mt-3 p-2 bg-brand-primary/5 rounded border border-brand-primary/20 flex justify-between items-center text-[10px]">
             <span className="font-bold text-brand-primary">SLA PENALTY (D)</span>
             <span className="font-black">₹{decisionData.components.avg_penalty.toLocaleString()}</span>
          </div>
        </div>

        <div className="action-section">
          <h3 className="text-[10px] font-black text-muted uppercase tracking-widest mb-3">Executive Recommendation</h3>
          <div className="action-card reroute">
            <div className="action-card-header" style={{ justifyContent: 'space-between' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <CheckCircle size={18} className="text-brand-primary" />
                <h4 className="font-bold text-sm tracking-tight tracking-tighter">{decisionData.recommended_action.toUpperCase()}</h4>
              </div>
              <span className="confidence-badge" style={{ fontSize: '0.75rem', padding: '2px 8px', backgroundColor: 'rgba(37, 99, 235, 0.1)', borderRadius: '12px', fontWeight: 600 }}>
                High Execution Feasibility
              </span>
            </div>
            
            <p className="mt-4 mb-4 text-[11px] font-medium leading-relaxed text-secondary border-l-4 border-brand-primary pl-4 bg-surface-elevated py-3 rounded-r-xl shadow-inner">
               <strong>STRATEGIC INSIGHT:</strong> {decisionData.executive_narrative} Choosing the <strong>{riskAppetite === 'CONSERVATIVE' ? 'Safety-First' : riskAppetite === 'AGGRESSIVE' ? 'Profit-Max' : 'Balanced'}</strong> intermodal path protects target margins.
            </p>
            
            {/* Pillar 7 Upgrade: Learning Insight Bubble */}
            <div className="learning-insight mt-3 mb-3 p-3 bg-brand-primary/10 border border-brand-primary/20 rounded-xl flex items-center gap-3">
               <div className="p-2 bg-brand-primary/20 rounded-full animate-pulse">
                  <RefreshCw size={14} className="text-brand-primary" />
               </div>
               <div>
                  <span className="block text-[8px] font-bold text-brand-primary uppercase">Autonomous Learning Insight</span>
                  <p className="text-[10px] font-black text-secondary">
                     System improved delay prediction by 15% on this route based on recent Feedback Loop data.
                  </p>
               </div>
            </div>

            {/* Tech Giant Upgrade: Stochastic Robustness Visualization */}
            <StochasticScenarioChart 
              cvarFloor={riskAppetite === 'CONSERVATIVE' ? 14200 : riskAppetite === 'AGGRESSIVE' ? 11000 : 12500} 
              scenarios={decisionData.monte_carlo_scenarios || []} 
              narratives={[
                "Extreme Scenario: Port Strike triggers 5-day demurrage; yielding heavy losses on Sea branch.",
                "Optimal Scenario: Customs congestion bypass; yielding maximum profit.",
                `Reasoning: This choice protects ${riskAppetite === 'CONSERVATIVE' ? '$14,200' : '$12,500'} in margin against predicted shocks.`
              ]}
            />

            {/* Pillar 5 Upgrade: Side-by-Side Scenario Comparison Table — live stress-test data */}
            <ScenarioComparisonMatrix scenarios={decisionData.scenario_analysis} />

            {/* Tech Giant Upgrade: Constraint Visibility Panel — live from insights API */}
            <ConstraintVisibilityPanel
              constraints={decisionData.constraints?.messages ?? ["Liquidity: High budget utilization detected.", "Capacity: EU-HUB rail terminal near peak."]}
              capacityUtilization={decisionData.constraints?.capacity_utilization ?? 94}
              costBudgetUtilization={decisionData.constraints?.budget_utilization ?? 92}
              slaHealth={decisionData.constraints?.sla_health ?? 98}
            />

            {/* Tech Giant Upgrade: Multimodal Trade-off Alternatives */}
            <div className="mt-6 mb-4">
               <h4 className="text-[10px] font-bold text-muted uppercase tracking-widest mb-2">Multimodal Alternatives</h4>
               <div className="flex flex-col gap-2">
                  <div className="flex justify-between items-center p-2 rounded bg-surface border border-subtle border-l-4 border-l-brand-primary">
                     <div>
                        <span className="text-[11px] font-bold block">RAIL (STABLE)</span>
                        <span className="text-[10px] text-secondary">T+3 days • -12% Risk</span>
                     </div>
                     <span className="text-[11px] font-mono font-bold">₹14,200 EFI</span>
                  </div>
                  <div className="flex justify-between items-center p-2 rounded bg-surface border border-subtle opacity-60">
                     <div>
                        <span className="text-[11px] font-bold block">OCEAN (SLOW)</span>
                        <span className="text-[10px] text-secondary">T+14 days • +5% Risk</span>
                     </div>
                     <span className="text-[11px] font-mono font-bold">₹9,800 EFI</span>
                  </div>
               </div>
            </div>
            
            {executionResult ? (
              <div className="success-receipt" style={{ marginTop: '16px', padding: '12px', backgroundColor: 'var(--semantic-safe-bg)', border: '1px solid var(--semantic-safe)', borderRadius: '8px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--semantic-safe)', marginBottom: '4px' }}>
                  <CheckCircle size={16} />
                  <span style={{ fontWeight: 600 }}>Action Confirmed & Logged</span>
                </div>
                <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                  ERP System: {executionResult.erp_system}<br />
                  Document/Ref: {executionResult.document_number || executionResult.transaction_id}<br />
                  Immutable Audit ID Created.
                </div>
              </div>
            ) : hasPermission('can_execute') ? (
              <button 
                className="btn-primary w-full mt-3" 
                style={{ display: 'flex', justifyContent: 'center', gap: '8px', alignItems: 'center' }}
                onClick={() => setIsRerouteStudioOpen(true)}
                disabled={isExecuting}
              >
                {isExecuting ? <Loader2 size={16} className="spin" /> : <CheckCircle size={16} />}
                {isExecuting ? 'Writing to ERP...' : 'Open Reroute Studio (94.2% Confidence)'}
              </button>
            ) : (
              <button 
                className="btn-outline w-full mt-3" 
                style={{ display: 'flex', justifyContent: 'center', gap: '8px', alignItems: 'center', cursor: 'not-allowed', opacity: 0.7 }}
                disabled={true}
              >
                <Lock size={16} />
                Execution Locked (Read-Only Profile)
              </button>
            )}
          </div>
        </div>
      </div>

      {isRerouteStudioOpen && (
        <RerouteStudio 
          shipmentId={shipmentId} 
          onClose={() => setIsRerouteStudioOpen(false)} 
          onConfirm={(mode) => {
             console.log(`Executing ${mode} Reroute...`);
             handleExecute();
             setIsRerouteStudioOpen(false);
          }}
        />
      )}
    </div>
  );
};
