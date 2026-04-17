import React, { useState } from 'react';
import { KPICard } from './KPICard';
import { AlertTriangle, ShieldCheck, Activity, CheckCircle, Download, FileSpreadsheet, Bell } from 'lucide-react';
import { CashflowChart } from './CashflowChart';
import FreightArbitrageEngine from './FreightArbitrageEngine';
import SpatialGridOverlay from '../matrix/SpatialGridOverlay';
import VisionDiagnosticModal from '../ingestion/VisionDiagnosticModal';
import RecoveryDashboard from '../revenue/RecoveryDashboard';
import { useExecutiveOverview } from '../../hooks/queries';
import { apiService } from '../../services/api';
import { useCurrency } from '../../context/CurrencyContext';
import { formatCurrency } from '../../utils/currency';

export const Dashboard: React.FC = () => {
  const [hasShocks]       = useState(true);
  const { currency, fxRate, toggle: toggleCurrency, rateLabel } = useCurrency();
  const [showVision, setShowVision]     = useState(false);
  const [alerts, setAlerts]             = useState<any[]>([]);
  const [alertsChecked, setAlertsChecked] = useState(false);
  const [exportingExcel, setExportingExcel] = useState(false);

  const handleExportExcel = async () => {
    setExportingExcel(true);
    try {
      const resp = await apiService.downloadExcel();
      if (!resp.ok) throw new Error('Export failed');
      const blob = await resp.blob();
      const url  = URL.createObjectURL(blob);
      const a    = document.createElement('a');
      a.href     = url;
      a.download = `fiscalogix_report_${new Date().toISOString().slice(0,10)}.xlsx`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      console.error('Excel export failed:', e);
    } finally {
      setExportingExcel(false);
    }
  };

  const handleCheckAlerts = async () => {
    try {
      const result = await apiService.checkAlerts();
      setAlerts(result.alerts ?? []);
      setAlertsChecked(true);
    } catch (e) {
      console.error('Alert check failed:', e);
    }
  };

  const { data, isLoading: loading } = useExecutiveOverview();

  // Derive KPI values from live data when available, else show safe placeholders
  const summary = data?.summary;
  const confidence = data?.confidence?.global_score;
  const shocks = data?.shocks ?? [];
  const waccBurn = data?.financial_impact?.wacc_cost;
  const tlcExposure = summary ? Math.abs(summary.total_cost - summary.total_revm) : null;

  // EFI copilot block: use real breakdown from FinancialAggregator when available
  const bd = summary?.breakdown;
  const efiPayload = summary
    ? {
        headline: `Estimated Financial Impact: ${summary.total_revm < 0 ? formatCurrency(summary.total_revm, currency, fxRate) + ' loss' : formatCurrency(summary.total_revm, currency, fxRate) + ' protected'}`,
        breakdown: {
          delay_cost:       bd?.delay_cost        ?? 0,
          penalty:          bd?.penalty_cost       ?? 0,
          inventory_cost:   bd?.inventory_holding  ?? 0,
          opportunity_cost: bd?.opportunity_cost   ?? 0,
        },
        recommended_action: summary.loss_shipments > 0
          ? `${summary.loss_shipments} shipment(s) at negative ReVM — review reroute options in Intelligence Matrix.`
          : 'All shipments operating at positive ReVM. No immediate rerouting required.',
        roi_improvement: '',
        new_loss: '',
      }
    : {
        headline: 'Loading financial intelligence...',
        breakdown: { delay_cost: 0, penalty: 0, inventory_cost: 0, opportunity_cost: 0 },
        recommended_action: 'Awaiting live data from the financial engine.',
        roi_improvement: '',
        new_loss: '',
      };

  return (
    <div className="dashboard-container">
      <header className="dashboard-header glass-panel">
        <div>
          <h1 className="page-title">Executive Dashboard</h1>
          <p className="page-subtitle">Pillars 1-13: Systemic Risk &amp; Capital Optimization</p>
        </div>
        <div className="header-actions">
          <button
            className="btn-secondary"
            onClick={toggleCurrency}
            title={rateLabel}
            style={{ fontWeight: 700, letterSpacing: '0.04em', minWidth: 72 }}
          >
            {currency === 'USD' ? '$ USD' : '₹ INR'}
          </button>
          <button className="btn-secondary" onClick={() => setShowVision(true)}>
            <Activity size={16} /> Vision Scan
          </button>
          <button className="btn-secondary" onClick={handleCheckAlerts} title="Check live alerts">
            <Bell size={16} />
            {alertsChecked && alerts.length > 0 && (
              <span style={{ marginLeft: 4, background: 'var(--semantic-critical)', borderRadius: '50%', padding: '0 5px', fontSize: 10 }}>
                {alerts.length}
              </span>
            )}
          </button>
          <button className="btn-secondary" onClick={handleExportExcel} disabled={exportingExcel} title="Download Excel report">
            <FileSpreadsheet size={16} /> {exportingExcel ? 'Exporting...' : 'Export'}
          </button>
          <button className="btn-secondary" onClick={() => window.print()} title="Print / Save as PDF">
            <Download size={16} /> PDF
          </button>
          <button className="btn-primary">Global Simulation</button>
        </div>
      </header>

      {showVision && <VisionDiagnosticModal onClose={() => setShowVision(false)} />}

      {/* Live alert banner — shown after manual check */}
      {alertsChecked && alerts.length > 0 && (
        <section style={{ marginBottom: 16 }}>
          {alerts.map((a: any, i: number) => (
            <div key={i} className={`alert-item ${a.severity === 'critical' ? 'critical' : 'warning'}`}
              style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '10px 16px', marginBottom: 6, borderRadius: 8 }}>
              <AlertTriangle size={16} />
              <div style={{ flex: 1 }}>
                <strong>{a.event_type.replace(/_/g, ' ')}</strong>
                <p style={{ margin: 0, fontSize: 12 }}>{a.message}</p>
              </div>
              <button className="btn-outline" style={{ fontSize: 11 }} onClick={() => setAlerts(prev => prev.filter((_, j) => j !== i))}>Dismiss</button>
            </div>
          ))}
        </section>
      )}
      {alertsChecked && alerts.length === 0 && (
        <div style={{ marginBottom: 16, padding: '10px 16px', borderRadius: 8, background: 'rgba(74,222,128,0.08)', border: '1px solid rgba(74,222,128,0.3)', display: 'flex', alignItems: 'center', gap: 8 }}>
          <CheckCircle size={16} color="var(--semantic-safe)" />
          <span style={{ fontSize: 12 }}>No alerts — all thresholds are within normal range.</span>
        </div>
      )}

      {/* TOP KPI SECTION */}
      <section className="kpi-grid">
        <KPICard
          title="Protected EBITDA"
          value={loading ? '—' : summary ? formatCurrency(summary.total_profit, currency, fxRate) : '₹4.2Cr'}
          trend={12}
          trendLabel="recovery active"
          icon={<ShieldCheck size={20} />}
          status={summary && summary.total_profit < 0 ? 'critical' : 'safe'}
        />
        <KPICard
          title="Capital Burn (WACC)"
          value={loading ? '—' : waccBurn != null ? formatCurrency(waccBurn, currency, fxRate) : '₹14.5L'}
          trend={-2.4}
          trendLabel="reduced decay"
          icon={<Activity size={20} />}
          status="neutral"
        />
        <KPICard
          title="TLC Exposure"
          value={loading ? '—' : tlcExposure != null ? formatCurrency(tlcExposure, currency, fxRate) : '₹82L'}
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
