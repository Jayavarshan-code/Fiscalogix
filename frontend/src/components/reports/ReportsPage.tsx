import React, { useState } from 'react';
import {
  FileSpreadsheet, Download, RefreshCw, TrendingDown,
  TrendingUp, Package, AlertTriangle, CheckCircle,
  BarChart3, Users, Anchor,
} from 'lucide-react';
import { apiService } from '../../services/api';
import { useExecutiveOverview } from '../../hooks/queries';

// ── Types ──────────────────────────────────────────────────────────────────────

interface ReportSummary {
  tenant_id: string;
  generated_at: string;
  shipment_count: number;
  total_revenue: number;
  total_cost: number;
  avg_delay_days: number;
  total_revm: number;
}

interface CarrierGapRow {
  carrier: string;
  total_gap_days: number;
  avg_gap_days: number;
  shipment_count: number;
  cash_tied_up: number;
  risk_level: string;
}

interface ConcentrationAlert {
  type: string;
  entity: string;
  share_pct: number;
  cash_impact_30d_delay: number;
  severity: string;
  recommendation: string;
}

// ── Helper ─────────────────────────────────────────────────────────────────────

const fmt = (v: number, prefix = '₹') => {
  if (Math.abs(v) >= 1e7) return `${prefix}${(v / 1e7).toFixed(2)}Cr`;
  if (Math.abs(v) >= 1e5) return `${prefix}${(v / 1e5).toFixed(2)}L`;
  return `${prefix}${v.toLocaleString('en-IN', { maximumFractionDigits: 0 })}`;
};

const riskColor = (r: string) =>
  r === 'HIGH' ? '#ef4444' : r === 'MEDIUM' ? '#f59e0b' : '#4ade80';

// ── Component ─────────────────────────────────────────────────────────────────

export const ReportsPage: React.FC = () => {
  const [exporting, setExporting] = useState(false);
  const [summary, setSummary]     = useState<ReportSummary | null>(null);
  const [loadingSummary, setLoadingSummary] = useState(false);
  const [summaryError, setSummaryError]     = useState<string | null>(null);

  // Pull carrier_gap and concentration from the main orchestrator response
  const { data, isLoading: orchLoading } = useExecutiveOverview();
  const carrierGap: CarrierGapRow[]          = (data as any)?.carrier_gap?.carriers ?? [];
  const concentrationAlerts: ConcentrationAlert[] = (data as any)?.concentration?.alerts ?? [];
  const financialImpact = (data as any)?.financial_impact ?? {};

  const handleExcelExport = async () => {
    setExporting(true);
    try {
      const resp = await apiService.downloadExcel();
      if (!resp.ok) throw new Error('Export failed');
      const blob = await resp.blob();
      const url  = URL.createObjectURL(blob);
      const a    = document.createElement('a');
      a.href     = url;
      a.download = `fiscalogix_report_${new Date().toISOString().slice(0, 10)}.xlsx`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e: any) {
      console.error('Excel export failed:', e);
    } finally {
      setExporting(false);
    }
  };

  const handleLoadSummary = async () => {
    setLoadingSummary(true);
    setSummaryError(null);
    try {
      const data = await apiService.getReportSummary();
      setSummary(data);
    } catch (e: any) {
      setSummaryError(e.message || 'Failed to load summary.');
    } finally {
      setLoadingSummary(false);
    }
  };

  const handlePrint = () => window.print();

  return (
    <div className="p-8 max-w-5xl mx-auto">
      {/* Header */}
      <header style={{ marginBottom: 32, display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <h1 className="page-title" style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <FileSpreadsheet size={24} /> Reports &amp; Export
          </h1>
          <p className="page-subtitle">
            CFO-ready Excel workbooks, JSON summaries, and freight analytics — all in INR.
          </p>
        </div>
        <div style={{ display: 'flex', gap: 10 }}>
          <button
            className="btn-secondary"
            onClick={handlePrint}
            style={{ display: 'flex', alignItems: 'center', gap: 8 }}
          >
            <Download size={15} /> Print / PDF
          </button>
          <button
            className="btn-primary"
            onClick={handleExcelExport}
            disabled={exporting}
            style={{ display: 'flex', alignItems: 'center', gap: 8 }}
          >
            <FileSpreadsheet size={15} />
            {exporting ? 'Generating...' : 'Export Excel (4 Sheets)'}
          </button>
        </div>
      </header>

      {/* Excel Export Info */}
      <section className="glass-panel" style={{ padding: 24, marginBottom: 24 }}>
        <h2 style={{ fontSize: 14, fontWeight: 700, marginBottom: 16 }}>Excel Workbook Contents</h2>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 16 }}>
          {[
            { sheet: 'KPI Summary',      desc: 'Total revenue, cost, ReVM, loss shipments, avg delay' },
            { sheet: 'Shipment Detail',  desc: 'Per-shipment REVM, delay cost, WACC, SLA penalty' },
            { sheet: 'AR Aging',         desc: '5-bucket receivables aging with action items' },
            { sheet: 'Carrier Gap',      desc: 'Working capital gap per carrier with risk rating' },
          ].map(({ sheet, desc }) => (
            <div key={sheet} style={{ padding: '14px 16px', borderRadius: 8, background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.08)' }}>
              <p style={{ fontWeight: 700, fontSize: 12, marginBottom: 6 }}>{sheet}</p>
              <p style={{ fontSize: 11, color: 'var(--text-muted)' }}>{desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* KPI Summary */}
      <section className="glass-panel" style={{ padding: 24, marginBottom: 24 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 18 }}>
          <h2 style={{ fontSize: 14, fontWeight: 700, display: 'flex', alignItems: 'center', gap: 8 }}>
            <BarChart3 size={16} /> KPI Summary
          </h2>
          <button
            className="btn-secondary"
            onClick={handleLoadSummary}
            disabled={loadingSummary}
            style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 12 }}
          >
            <RefreshCw size={13} />
            {loadingSummary ? 'Loading...' : 'Load Live Summary'}
          </button>
        </div>

        {summaryError && <p style={{ color: 'var(--semantic-critical)', fontSize: 13 }}>{summaryError}</p>}

        {summary ? (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16 }}>
            <KPITile label="Shipments Processed" value={summary.shipment_count.toLocaleString()} icon={<Package size={16} />} />
            <KPITile label="Total Revenue" value={fmt(summary.total_revenue)} icon={<TrendingUp size={16} />} />
            <KPITile label="Total Cost" value={fmt(summary.total_cost)} icon={<TrendingDown size={16} />} />
            <KPITile
              label="Total ReVM"
              value={fmt(summary.total_revm)}
              icon={summary.total_revm >= 0 ? <CheckCircle size={16} /> : <AlertTriangle size={16} />}
              status={summary.total_revm >= 0 ? 'safe' : 'critical'}
            />
            <KPITile label="Avg Delay" value={`${summary.avg_delay_days.toFixed(1)} days`} icon={<RefreshCw size={16} />} />
            <KPITile label="Generated" value={new Date(summary.generated_at).toLocaleDateString('en-IN')} icon={<FileSpreadsheet size={16} />} />
          </div>
        ) : (
          <p style={{ fontSize: 13, color: 'var(--text-muted)' }}>
            Click "Load Live Summary" to pull current KPIs from the database.
          </p>
        )}
      </section>

      {/* Financial Impact Block */}
      {financialImpact && Object.keys(financialImpact).length > 0 && (
        <section className="glass-panel" style={{ padding: 24, marginBottom: 24 }}>
          <h2 style={{ fontSize: 14, fontWeight: 700, marginBottom: 18, display: 'flex', alignItems: 'center', gap: 8 }}>
            <TrendingUp size={16} /> Financial Impact (Fiscalogix Recommendations)
          </h2>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 16 }}>
            <KPITile label="Unlocked Working Capital" value={fmt(financialImpact.unlocked_working_capital ?? 0)} status="safe" />
            <KPITile label="Annualized Free Cash Flow" value={fmt(financialImpact.annualized_savings ?? 0)} status="safe" />
            <KPITile label="SLA Penalties Avoided" value={fmt(financialImpact.sla_penalties_avoided ?? 0)} />
            <KPITile label="VaR Exposure Mitigated (40%)" value={fmt(financialImpact.risk_exposure_mitigated ?? 0)} />
          </div>
          {financialImpact.cfo_narrative && (
            <div style={{ marginTop: 18, padding: '14px 18px', borderRadius: 8, background: 'rgba(99,102,241,0.08)', border: '1px solid rgba(99,102,241,0.2)', fontSize: 13, lineHeight: 1.65 }}>
              {financialImpact.cfo_narrative}
            </div>
          )}
        </section>
      )}

      {/* Carrier Gap Analysis */}
      <section className="glass-panel" style={{ padding: 24, marginBottom: 24 }}>
        <h2 style={{ fontSize: 14, fontWeight: 700, marginBottom: 6, display: 'flex', alignItems: 'center', gap: 8 }}>
          <Anchor size={16} /> Carrier Gap Analysis
        </h2>
        <p style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 18 }}>
          Days between carrier payment due and client collection — the working capital you fund in between.
        </p>

        {orchLoading ? (
          <p style={{ fontSize: 13, color: 'var(--text-muted)' }}>Loading carrier data...</p>
        ) : carrierGap.length === 0 ? (
          <p style={{ fontSize: 13, color: 'var(--text-muted)' }}>
            No carrier gap data yet. Upload shipment data via the Data Warehouse to populate this view.
          </p>
        ) : (
          <table style={{ width: '100%', fontSize: 13, borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.1)', color: 'var(--text-muted)', fontSize: 11, textTransform: 'uppercase' }}>
                <th style={th}>Carrier</th>
                <th style={th}>Shipments</th>
                <th style={th}>Avg Gap (days)</th>
                <th style={th}>Cash Tied Up</th>
                <th style={th}>Risk</th>
              </tr>
            </thead>
            <tbody>
              {carrierGap.map((row, i) => (
                <tr key={i} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                  <td style={td}><strong>{row.carrier}</strong></td>
                  <td style={td}>{row.shipment_count}</td>
                  <td style={td}>{row.avg_gap_days?.toFixed(1) ?? '—'}</td>
                  <td style={td}>{fmt(row.cash_tied_up ?? 0)}</td>
                  <td style={td}>
                    <span style={{
                      fontSize: 11, fontWeight: 700, padding: '3px 8px', borderRadius: 4,
                      background: riskColor(row.risk_level) + '22',
                      color: riskColor(row.risk_level),
                    }}>
                      {row.risk_level}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      {/* Concentration Risk */}
      <section className="glass-panel" style={{ padding: 24 }}>
        <h2 style={{ fontSize: 14, fontWeight: 700, marginBottom: 6, display: 'flex', alignItems: 'center', gap: 8 }}>
          <Users size={16} /> Concentration Risk
        </h2>
        <p style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 18 }}>
          Entities exceeding safe concentration thresholds (30% client revenue / 50% port volume).
        </p>

        {orchLoading ? (
          <p style={{ fontSize: 13, color: 'var(--text-muted)' }}>Loading concentration data...</p>
        ) : concentrationAlerts.length === 0 ? (
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '14px 18px', borderRadius: 8, background: 'rgba(74,222,128,0.08)', border: '1px solid rgba(74,222,128,0.25)' }}>
            <CheckCircle size={16} color="#4ade80" />
            <span style={{ fontSize: 13 }}>No concentration risk flags — portfolio is well-distributed.</span>
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            {concentrationAlerts.map((a, i) => (
              <div
                key={i}
                style={{
                  padding: '14px 18px', borderRadius: 8,
                  background: a.severity === 'critical' ? 'rgba(239,68,68,0.07)' : 'rgba(245,158,11,0.07)',
                  border: `1px solid ${riskColor(a.severity === 'critical' ? 'HIGH' : 'MEDIUM')}33`,
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
                  <strong style={{ fontSize: 13 }}>
                    {a.type === 'client' ? <Users size={13} style={{ display: 'inline', marginRight: 5 }} /> : <Anchor size={13} style={{ display: 'inline', marginRight: 5 }} />}
                    {a.entity}
                  </strong>
                  <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                    {(a.share_pct * 100).toFixed(1)}% of {a.type === 'client' ? 'revenue' : 'volume'}
                  </span>
                </div>
                <p style={{ fontSize: 12, color: 'var(--text-secondary)', margin: '0 0 6px' }}>
                  30-day payment delay impact: <strong>{fmt(a.cash_impact_30d_delay ?? 0)}</strong>
                </p>
                <p style={{ fontSize: 11, color: 'var(--text-muted)', margin: 0 }}>{a.recommendation}</p>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
};

// ── Sub-components ─────────────────────────────────────────────────────────────

interface KPITileProps {
  label: string;
  value: string;
  icon?: React.ReactNode;
  status?: 'safe' | 'critical' | 'warning';
}

const KPITile: React.FC<KPITileProps> = ({ label, value, icon, status }) => {
  const borderColor =
    status === 'safe'     ? 'rgba(74,222,128,0.3)' :
    status === 'critical' ? 'rgba(239,68,68,0.3)'  :
    status === 'warning'  ? 'rgba(245,158,11,0.3)' :
    'rgba(255,255,255,0.08)';

  return (
    <div style={{
      padding: '14px 18px', borderRadius: 8,
      background: 'rgba(255,255,255,0.03)',
      border: `1px solid ${borderColor}`,
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 7, marginBottom: 8, color: 'var(--text-muted)', fontSize: 11 }}>
        {icon}
        {label}
      </div>
      <p style={{ fontSize: 20, fontWeight: 700, margin: 0 }}>{value}</p>
    </div>
  );
};

const th: React.CSSProperties = {
  padding: '8px 12px', textAlign: 'left', fontWeight: 600,
};
const td: React.CSSProperties = {
  padding: '10px 12px', color: 'var(--text-secondary)',
};

export default ReportsPage;
