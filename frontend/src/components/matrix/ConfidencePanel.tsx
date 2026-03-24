import React, { useState } from 'react';
import { X, CheckCircle, ShieldAlert, Loader2, Lock } from 'lucide-react';
import { apiService } from '../../services/api';
import { useAuth } from '../../context/AuthContext';
import { TemporalRiskTimeline } from './TemporalRiskTimeline';
import { StochasticScenarioChart } from './StochasticScenarioChart';
import { RerouteStudio } from './RerouteStudio';
import './ConfidencePanel.css';

interface ConfidencePanelProps {
  shipmentId: string | null;
  onClose: () => void;
}

export const ConfidencePanel: React.FC<ConfidencePanelProps> = ({ shipmentId, onClose }) => {
  const [isExecuting, setIsExecuting] = useState(false);
  const [isRerouteStudioOpen, setIsRerouteStudioOpen] = useState(false);
  const [executionResult, setExecutionResult] = useState<any>(null);
  const { currentUser, hasPermission } = useAuth();

  if (!shipmentId) return null;

  const handleExecute = async () => {
    setIsExecuting(true);
    try {
      const result = await apiService.executeAction({
        tenant_id: 'default_tenant',
        action_type: 'REROUTE_AIR_FREIGHT',
        shipment_id: shipmentId,
        erp_target: 'SAP',
        confidence_score: 0.942,
        mock_user_id: currentUser?.id || 1
      });
      setExecutionResult(result.erp_receipt);
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
          <h2>Confidence Studio</h2>
          <span className="subtitle">Explaining action for {shipmentId}</span>
        </div>
        <button className="icon-btn" onClick={onClose}><X size={20} /></button>
      </div>

      <div className="panel-body">
        <div className="score-section">
          <div className="score-circle critical">
            <span className="score-value">85%</span>
            <span className="score-label">Risk Probability</span>
          </div>
          <div className="score-context">
            <ShieldAlert className="text-critical" size={24} />
            <div>
              <h4>Critical Intervention Required</h4>
              <p>Model confidence: 94.2% (High Integrity)</p>
            </div>
          </div>
        </div>

        {/* Tech Giant Upgrade: Temporal Risk Timeline */}
        <TemporalRiskTimeline markers={[
            { time_hours: 0, score: 0.15, label: 'Origin (Rotterdam)' },
            { time_hours: 24, score: 0.87, label: 'Hub Contagion' },
            { time_hours: 48, score: 0.92, label: 'Destination Shock' }
        ]} />

        <div className="drivers-section">
          <h3>Top Structural Drivers</h3>
          <ul className="driver-list">
            <li className="driver-item warning">
              <span className="driver-name">Carrier Performance Degradation</span>
              <span className="driver-impact">+32%</span>
            </li>
            <li className="driver-item critical">
              <span className="driver-name">Margin Compression vs Spot Rate</span>
              <span className="driver-impact">+45%</span>
            </li>
            <li className="driver-item safe">
              <span className="driver-name">Inventory Buffer Status</span>
              <span className="driver-impact">-12%</span>
            </li>
          </ul>
        </div>

        <div className="action-section">
          <h3>Recommended Action</h3>
          <div className="action-card reroute">
            <div className="action-card-header" style={{ justifyContent: 'space-between' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <CheckCircle size={18} />
                <h4>REROUTE TO AIR FREIGHT</h4>
              </div>
              <span className="confidence-badge" style={{ fontSize: '0.75rem', padding: '2px 8px', backgroundColor: 'rgba(37, 99, 235, 0.1)', borderRadius: '12px', fontWeight: 600 }}>
                94.2% Confidence
              </span>
            </div>
            
            <p className="mt-2 mb-4 text-xs leading-relaxed text-secondary border-l-2 border-brand-primary pl-3 bg-surface-elevated py-2 rounded-r">
               <strong>XAI ADVISORY:</strong> Rerouting initiated due to <strong>87% probability</strong> of strike contagion propagating from 
               <strong> PORT_A</strong> to <strong>HUB_B</strong> in <strong>T+24h</strong>. This proactive shift preserves <strong>$15,000</strong> in expected ReVM 
               and maintains a <strong>$12,500 robustness floor</strong> against 90th percentile market shocks.
            </p>
            
            {/* Tech Giant Upgrade: Stochastic Robustness Visualization */}
            <StochasticScenarioChart 
              cvarFloor={12500} 
              scenarios={[
                14000, 15500, 12000, 8000, 15000, 16000, 13000, 14500, 12500, 11000,
                15200, 14800, 13900, 12100, 11500, 16200, 15800, 14200, 12600, 13100
              ]} 
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
                     <span className="text-[11px] font-mono font-bold">$14,200 ReVM</span>
                  </div>
                  <div className="flex justify-between items-center p-2 rounded bg-surface border border-subtle opacity-60">
                     <div>
                        <span className="text-[11px] font-bold block">OCEAN (SLOW)</span>
                        <span className="text-[10px] text-secondary">T+14 days • +5% Risk</span>
                     </div>
                     <span className="text-[11px] font-mono font-bold">$9,800 ReVM</span>
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
