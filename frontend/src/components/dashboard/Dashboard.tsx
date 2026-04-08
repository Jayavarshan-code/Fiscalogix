import React, { useState } from 'react';
import { KPICard } from './KPICard';
import { AlertTriangle, ShieldCheck, Activity, CheckCircle } from 'lucide-react';
import { CashflowChart } from './CashflowChart';
import FreightArbitrageEngine from './FreightArbitrageEngine';
import SpatialGridOverlay from '../matrix/SpatialGridOverlay';
import VisionDiagnosticModal from '../ingestion/VisionDiagnosticModal';
import RecoveryDashboard from '../revenue/RecoveryDashboard';
import { useExecutiveOverview } from '../../hooks/queries';

// Shape of the /financial-intelligence response is now imported via queries if needed

const fmt = (val: number, currency = '₹') =>
  `${currency}${Math.abs(val).toLocaleString('en-IN', { maximumFractionDigits: 0 })}`;

export const Dashboard: React.FC = () => {
  const [hasShocks, setHasShocks] = useState(true);
  const [showVision, setShowVision] = useState(false);

  const { data, isLoading: loading } = useExecutiveOverview();

  // Derive KPI values from live data when available, else show safe placeholders
  const summary = data?.summary;
  const confidence = data?.confidence?.global_score;
  const shocks = data?.shocks ?? [];
  const waccBurn = data?.financial_impact?.wacc_cost;
  const tlcExposure = summary ? Math.abs(summary.total_cost - summary.total_revm) : null;

  // EFI copilot block: prefer live data, fall back to demo narrative
  const efiPayload = summary
    ? {
        headline: `Estimated Financial Impact: ${summary.total_revm < 0 ? fmt(summary.total_revm) + ' loss' : fmt(summary.total_revm) + ' protected'}`,
        breakdown: {
          delay_cost: 0,
          penalty: 0,
          inventory_cost: 0,
          opportunity_cost: 0,
        },
        recommended_action: summary.loss_shipments > 0
          ? `${summary.loss_shipments} shipment(s) at negative ReVM — review reroute options in Intelligence Matrix.`
          : 'All shipments operating at positive ReVM. No immediate rerouting required.',
        roi_improvement: '',
        new_loss: '',
      }
    : {
        headline: 'Estimated Financial Impact: ₹11,45,000 loss',
        breakdown: {
          delay_cost: 450000,
          penalty: 300000,
          inventory_cost: 245000,
          opportunity_cost: 150000,
        },
        recommended_action:
          'Reroute Shipment IN-09 via Colombo to bypass Singapore strike. Restores inventory availability by 48 hours.',
        roi_improvement: '42%',
        new_loss: '6,64,000',
      };

  return (
    <div className="dashboard-container">
      <header className="dashboard-header glass-panel">
        <div>
          <h1 className="page-title">Executive Dashboard</h1>
          <p className="page-subtitle">Pillars 1-13: Systemic Risk &amp; Capital Optimization</p>
        </div>
        <div className="header-actions">
          <button className="btn-secondary" onClick={() => setShowVision(true)}>
            <Activity size={16} /> Vision Scan
          </button>
          <button className="btn-secondary" onClick={() => setHasShocks(!hasShocks)}>
            Toggle Risks
          </button>
          <button className="btn-primary">Global Simulation</button>
        </div>
      </header>

      {showVision && <VisionDiagnosticModal onClose={() => setShowVision(false)} />}

      {/* TOP KPI SECTION */}
      <section className="kpi-grid">
        <KPICard
          title="Protected EBITDA"
          value={loading ? '—' : summary ? fmt(summary.total_profit) : '₹4.2Cr'}
          trend={12}
          trendLabel="recovery active"
          icon={<ShieldCheck size={20} />}
          status={summary && summary.total_profit < 0 ? 'critical' : 'safe'}
        />
        <KPICard
          title="Capital Burn (WACC)"
          value={loading ? '—' : waccBurn != null ? fmt(waccBurn) : '₹14.5L'}
          trend={-2.4}
          trendLabel="reduced decay"
          icon={<Activity size={20} />}
          status="neutral"
        />
        <KPICard
          title="TLC Exposure"
          value={loading ? '—' : tlcExposure != null ? fmt(tlcExposure) : '₹82L'}
          trend={5.1}
          trendLabel="Tariff Volatility"
          icon={<AlertTriangle size={20} />}
          status={tlcExposure != null && tlcExposure > 5000000 ? 'critical' : 'warning'}
        />
        <KPICard
          title="System Confidence"
          value={loading ? '—' : confidence != null ? `${(confidence * 100).toFixed(1)}%` : '98.2%'}
          trend={1.2}
          trendLabel="Hardened Tuning"
          icon={<CheckCircle size={20} />}
          status={confidence != null && confidence < 0.7 ? 'warning' : 'safe'}
        />
      </section>

      {/* MIDDLE SECTION: Spatial & Financial Integration */}
      <section className="charts-grid">
        <div className="premium-card chart-card glass-panel">
          <div className="card-header">
            <h3>H3 Spatial Risk Topology</h3>
          </div>
          <SpatialGridOverlay />
        </div>

        <div className="premium-card chart-card glass-panel">
          <div className="card-header">
            <h3>Cashflow Trajectory (Risk-Adjusted)</h3>
          </div>
          <CashflowChart />
        </div>
      </section>

      {/* PERSISTENT COPILOT: THE 3-TIER TRUST LAYER */}
      <FreightArbitrageEngine {...efiPayload} />

      {/* PHASE 3: REVENUE RECOVERY ENGINE */}
      <section className="recovery-section">
        <h3 className="section-title">Revenue Recovery Engine</h3>
        <RecoveryDashboard />
      </section>

      {/* BOTTOM SECTION - Actionable Alerts */}
      <section className="alerts-section">
        <h3 className="section-title">Systemic Status</h3>

        {(hasShocks && (shocks.length > 0 || !data)) ? (
          <div className="alerts-list">
            {shocks.length > 0 ? (
              shocks.slice(0, 3).map((shock: any, idx: number) => (
                <div key={idx} className="alert-item critical">
                  <div className="alert-icon"><AlertTriangle size={16} /></div>
                  <div className="alert-content">
                    <h4>{shock.description || 'Supply Chain Shock Detected'}</h4>
                    <p>{shock.detail || `Severity: ${shock.severity_score ?? 'Unknown'}`}</p>
                  </div>
                  <button className="btn-outline">View Mitigation (POE)</button>
                </div>
              ))
            ) : (
              // Fallback alerts when not yet loaded from API
              <>
                <div className="alert-item critical">
                  <div className="alert-icon"><AlertTriangle size={16} /></div>
                  <div className="alert-content">
                    <h4>Projected Cash Deficit (-$45k) in 5 Days</h4>
                    <p>Network delays on Route EU-US are extending working capital cycles beyond current liquidity buffers.</p>
                  </div>
                  <button className="btn-outline">View Mitigation (POE)</button>
                </div>
                <div className="alert-item warning">
                  <div className="alert-icon"><AlertTriangle size={16} /></div>
                  <div className="alert-content">
                    <h4>Elevated Risk Exposure Cluster</h4>
                    <p>3 shipments at high risk due to EU port labor strikes. Confidence: 82%.</p>
                  </div>
                  <button className="btn-outline">Analyze Matrix</button>
                </div>
              </>
            )}
          </div>
        ) : (
          <div className="premium-card empty-state-card" style={{ textAlign: 'center', padding: '40px' }}>
            <CheckCircle size={48} color="var(--semantic-safe)" style={{ margin: '0 auto 16px' }} />
            <h4 style={{ fontSize: '1.25rem', marginBottom: '8px' }}>All Systems Nominal</h4>
            <p style={{ color: 'var(--text-secondary)' }}>
              No supply chain shocks or cashflow deficits detected within the 30-day projection window.
            </p>
          </div>
        )}
      </section>
    </div>
  );
};
