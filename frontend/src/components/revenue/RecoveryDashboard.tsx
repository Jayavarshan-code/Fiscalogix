import React, { useState, useEffect } from 'react';
import { apiService } from '../../services/api';
import './RecoveryDashboard.css';

interface RecoveryEvent {
  id: string;
  shipmentId: string;
  lossAmount: number;
  clause: string;
  status: 'detected' | 'drafted' | 'filed' | 'contested' | 'recovered';
  evidencePackRef: string;
  // Enriched by /enterprise/ar-default
  defaultProbability?: number;
  expectedCreditLoss?: number;
  arAction?: string;
}

// Seed data — in production these would come from a claims management endpoint
const SEED_EVENTS: RecoveryEvent[] = [
  {
    id: 'REV-001',
    shipmentId: 'LGX-992',
    lossAmount: 400000,
    clause: 'Clause 7.2: Delay Penalty',
    status: 'detected',
    evidencePackRef: 'EV_LGX992_20260331.zip',
  },
  {
    id: 'REV-002',
    shipmentId: 'LGX-104',
    lossAmount: 250000,
    clause: 'Clause 4.1: Demurrage Breach',
    status: 'contested',
    evidencePackRef: 'EV_LGX104_20260328.zip',
  },
];

const RecoveryDashboard: React.FC = () => {
  const [events, setEvents] = useState<RecoveryEvent[]>(SEED_EVENTS);
  const [arLoading, setArLoading] = useState(true);

  // Enrich claims with live AR default risk on mount
  useEffect(() => {
    const enrichWithARDefault = async () => {
      try {
        const customers = SEED_EVENTS.map(e => ({
          customer_id:         e.shipmentId,
          order_value:         e.lossAmount,
          credit_days:         30,
          historical_defaults: e.status === 'contested' ? 1 : 0,
        }));

        const results = await apiService.getARDefault(customers);

        // Map results back by customer_id
        const riskMap: Record<string, typeof results[0]> = {};
        for (const r of results) {
          riskMap[r.customer_id] = r;
        }

        setEvents(prev =>
          prev.map(e => {
            const risk = riskMap[e.shipmentId];
            return risk
              ? {
                  ...e,
                  defaultProbability:  risk.probability_of_default,
                  expectedCreditLoss:  risk.expected_credit_loss,
                  arAction:            risk.recommended_action,
                }
              : e;
          })
        );
      } catch (err) {
        console.error('AR default enrichment failed:', err);
      } finally {
        setArLoading(false);
      }
    };

    enrichWithARDefault();
  }, []);

  const handleGenerateClaim = (id: string) => {
    setEvents(prev => prev.map(e => e.id === id ? { ...e, status: 'drafted' } : e));
  };

  const handleFileClaim = (id: string) => {
    setEvents(prev => prev.map(e => e.id === id ? { ...e, status: 'filed' } : e));
  };

  const handleCounterClaim = (id: string) => {
    alert('Counter-Claim Authored: Attaching ACLED & MarineTraffic Database Logs.');
    setEvents(prev => prev.map(e => e.id === id ? { ...e, status: 'filed' } : e));
  };

  const handleDownloadEvidence = (fileName: string) => {
    alert(`Downloading Encrypted Evidence Package: ${fileName}\nIncludes: MSA.pdf, H3_Spatial_Logs.csv, Financial_Audit.json`);
  };

  const pendingRecovery = events
    .filter(e => ['drafted', 'filed', 'contested'].includes(e.status))
    .reduce((sum, e) => sum + e.lossAmount, 0);

  const defaultRiskLabel = (prob?: number) => {
    if (prob == null) return null;
    if (prob > 0.15) return { label: 'HIGH',   color: 'text-critical' };
    if (prob > 0.05) return { label: 'MEDIUM', color: 'text-warning'  };
    return              { label: 'LOW',    color: 'text-safe'    };
  };

  return (
    <div className="recovery-dashboard glass-panel">
      <div className="recovery-header">
        <h2>💰 Revenue Recovery Hub</h2>
        <div className="roi-stat">
          <span className="label">Pipeline Value (Pending / Contested):</span>
          <span className="value pending">₹ {(pendingRecovery / 100000).toFixed(1)}L</span>
        </div>
      </div>

      <div className="recovery-table">
        <table>
          <thead>
            <tr>
              <th>Shipment</th>
              <th>Detected Loss</th>
              <th>Clause Basis</th>
              <th>Status</th>
              <th>AR Default Risk</th>
              <th>Evidence</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {events.map(event => {
              const risk = defaultRiskLabel(event.defaultProbability);
              return (
                <tr key={event.id} className={event.status}>
                  <td>{event.shipmentId}</td>
                  <td className="loss-val">₹ {event.lossAmount.toLocaleString()}</td>
                  <td>{event.clause}</td>
                  <td>
                    <span className={`status-badge ${event.status}`}>
                      {event.status.toUpperCase()}
                    </span>
                  </td>
                  <td>
                    {arLoading ? (
                      <span className="text-muted text-xs">Loading...</span>
                    ) : risk ? (
                      <div>
                        <span className={`font-bold text-xs ${risk.color}`}>{risk.label}</span>
                        <span className="text-muted text-xs ml-1">
                          ({(event.defaultProbability! * 100).toFixed(1)}% PD)
                        </span>
                        {event.arAction && (
                          <div className="text-[10px] text-muted mt-0.5">{event.arAction}</div>
                        )}
                      </div>
                    ) : (
                      <span className="text-muted text-xs">—</span>
                    )}
                  </td>
                  <td>
                    <button className="btn-evidence" onClick={() => handleDownloadEvidence(event.evidencePackRef)}>
                      📦 Download .ZIP
                    </button>
                  </td>
                  <td>
                    {event.status === 'detected' && (
                      <button className="btn-action pulse" onClick={() => handleGenerateClaim(event.id)}>
                        Generate Claim
                      </button>
                    )}
                    {event.status === 'drafted' && (
                      <button className="btn-file" onClick={() => handleFileClaim(event.id)}>
                        File with Carrier
                      </button>
                    )}
                    {event.status === 'filed' && (
                      <span className="done-icon">✔ Sent to Carrier</span>
                    )}
                    {event.status === 'contested' && (
                      <button className="btn-action pulse-red" onClick={() => handleCounterClaim(event.id)}>
                        ⚠️ File Counter-Claim
                      </button>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {!arLoading && events.some(e => e.defaultProbability != null && e.defaultProbability > 0.05) && (
        <div className="hitl-note" style={{ borderColor: 'var(--semantic-warning)', background: 'rgba(245,158,11,0.05)' }}>
          <p>⚠️ <b>AR Risk Alert:</b> One or more claims carry elevated default probability. Consider invoice factoring or cash-in-advance terms before settlement.</p>
        </div>
      )}

      <div className="hitl-note">
        <p>💡 <b>Legal &amp; Compliance:</b> All Evidence `.ZIP` files are cryptographically hashed upon creation to ensure non-repudiation in arbitration.</p>
      </div>
    </div>
  );
};

export default RecoveryDashboard;
