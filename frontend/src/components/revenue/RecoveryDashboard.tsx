import React, { useState } from 'react';
import './RecoveryDashboard.css';

interface RecoveryEvent {
    id: string;
    shipmentId: string;
    lossAmount: number;
    clause: string;
    status: 'detected' | 'drafted' | 'filed' | 'contested' | 'recovered';
    evidencePackRef: string;
}

const RecoveryDashboard: React.FC = () => {
    const [events, setEvents] = useState<RecoveryEvent[]>([
        {
            id: 'REV-001',
            shipmentId: 'LGX-992',
            lossAmount: 400000,
            clause: 'Clause 7.2: Delay Penalty',
            status: 'detected',
            evidencePackRef: 'EV_LGX992_20260331.zip'
        },
        {
            id: 'REV-002',
            shipmentId: 'LGX-104',
            lossAmount: 250000,
            clause: 'Clause 4.1: Demurrage Breach',
            status: 'contested',
            evidencePackRef: 'EV_LGX104_20260328.zip'
        }
    ]);

    const handleGenerateClaim = (id: string) => {
        setEvents(prev => prev.map(e => 
            e.id === id ? { ...e, status: 'drafted' } : e
        ));
    };

    const handleFileClaim = (id: string) => {
        setEvents(prev => prev.map(e => 
            e.id === id ? { ...e, status: 'filed' } : e
        ));
    };

    const handleCounterClaim = (id: string) => {
        alert("Counter-Claim Authored: Attaching ACLED & MarineTraffic Database Logs.");
        setEvents(prev => prev.map(e => 
            e.id === id ? { ...e, status: 'filed' } : e
        ));
    };

    const handleDownloadEvidence = (fileName: string) => {
        alert(`Downloading Encrypted Evidence Package: ${fileName}\nIncludes: MSA.pdf, H3_Spatial_Logs.csv, Financial_Audit.json`);
    };

    const pendingRecovery = events
        .filter(e => ['drafted', 'filed', 'contested'].includes(e.status))
        .reduce((sum, e) => sum + e.lossAmount, 0);

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
                            <th>Evidence (Gap 2)</th>
                            <th>Actions (Gap 1)</th>
                        </tr>
                    </thead>
                    <tbody>
                        {events.map(event => (
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
                        ))}
                    </tbody>
                </table>
            </div>

            <div className="hitl-note">
                <p>💡 <b>Legal & Compliance:</b> All Evidence `.ZIP` files are cryptographically hashed upon creation to ensure non-repudiation in arbitration.</p>
            </div>
        </div>
    );
};

export default RecoveryDashboard;
