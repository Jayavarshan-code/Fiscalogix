import React, { useState } from 'react';
import { X, CheckCircle, ShieldAlert, Loader2, Lock } from 'lucide-react';
import { apiService } from '../../services/api';
import { useAuth } from '../../context/AuthContext';
import './ConfidencePanel.css';

interface ConfidencePanelProps {
  shipmentId: string | null;
  onClose: () => void;
}

export const ConfidencePanel: React.FC<ConfidencePanelProps> = ({ shipmentId, onClose }) => {
  const [isExecuting, setIsExecuting] = useState(false);
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
            <p>Prevents stockout. Preserves $15k REVM over current trajectory.</p>
            
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
                onClick={handleExecute}
                disabled={isExecuting}
              >
                {isExecuting ? <Loader2 size={16} className="spin" /> : <CheckCircle size={16} />}
                {isExecuting ? 'Writing to ERP...' : 'Execute POE Payload (94.2% Confidence)'}
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
    </div>
  );
};
