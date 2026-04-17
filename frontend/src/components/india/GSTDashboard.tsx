import React, { useState } from 'react';
import {
  IndianRupee, AlertTriangle, CheckCircle, TrendingDown,
  RefreshCw, ChevronDown, ChevronUp, Info, ArrowRight,
  FileText, Globe, Loader2,
} from 'lucide-react';
import { apiService } from '../../services/api';
import { useIndiaRoutes } from '../../hooks/queries';

// ── Types ─────────────────────────────────────────────────────────────────────

interface GSTShipmentInput {
  shipment_id: string;
  route: string;
  order_value: number;
  hs_code: string;
  gst_refund_mode: string;
}

interface GSTCostResult {
  shipment_id: string;
  direction: 'export' | 'import' | 'domestic';
  route: string;
  gst_rate?: number;
  igst_paid?: number;
  refund_mode?: string;
  refund_lag_days?: number;
  gst_working_capital_cost?: number;
  drawback_rate?: number;
  drawback_receivable?: number;
  net_gst_impact?: number;
  bcd_rate?: number;
  bcd_cost?: number;
  igst_on_import?: number;
  itc_working_capital_cost?: number;
  total_india_customs_cost?: number;
}

interface PortfolioSummary {
  total_locked_inr: number;
  total_working_capital_burn: number;
  annual_burn_inr: number;
  daily_burn_inr: number;
  stuck_claims: any[];   // backend returns array of stuck claim dicts
  stuck_count: number;   // backend returns count separately
  claims: any[];         // all claims
  by_type: Record<string, any>;
  tenant_id: string;
  wacc_used: number;
}

// ── Helpers ───────────────────────────────────────────────────────────────────

const fmt = (v: number, prefix = '₹') => {
  const abs = Math.abs(v);
  const sign = v < 0 ? '-' : '';
  if (abs >= 1e7) return `${sign}${prefix}${(abs / 1e7).toFixed(2)} Cr`;
  if (abs >= 1e5) return `${sign}${prefix}${(abs / 1e5).toFixed(2)} L`;
  return `${sign}${prefix}${abs.toLocaleString('en-IN', { maximumFractionDigits: 0 })}`;
};

const pct = (v: number) => `${(v * 100).toFixed(1)}%`;

const REFUND_MODES = [
  { value: 'lut',    label: 'LUT (Zero GST)',    desc: 'Registered under Letter of Undertaking — no upfront GST' },
  { value: 'auto',   label: 'Auto Refund',        desc: 'GSTN automated refund — ~30 day lag' },
  { value: 'manual', label: 'Manual Refund',       desc: 'Manual processing — ~75 day lag' },
  { value: 'stuck',  label: 'Stuck / Pending',    desc: 'Past SLA — 90+ days' },
];

const SAMPLE_PORTFOLIO: GSTShipmentInput[] = [
  { shipment_id: 'EXP-001', route: 'IN-US', order_value: 5000000, hs_code: '30',   gst_refund_mode: 'auto'   },
  { shipment_id: 'EXP-002', route: 'IN-EU', order_value: 3200000, hs_code: '62',   gst_refund_mode: 'manual' },
  { shipment_id: 'EXP-003', route: 'IN-AE', order_value: 1800000, hs_code: '84',   gst_refund_mode: 'stuck'  },
  { shipment_id: 'IMP-001', route: 'CN-IN', order_value: 2500000, hs_code: '85',   gst_refund_mode: 'auto'   },
  { shipment_id: 'IMP-002', route: 'EU-IN', order_value: 1200000, hs_code: '84',   gst_refund_mode: 'auto'   },
];

// ── Main Component ────────────────────────────────────────────────────────────

type Tab = 'tracker' | 'analyzer' | 'corridors';

export const GSTDashboard: React.FC = () => {
  const [activeTab, setActiveTab] = useState<Tab>('tracker');

  return (
    <div style={{ padding: 32, maxWidth: 1100, margin: '0 auto' }}>
      {/* Header */}
      <header style={{ marginBottom: 28 }}>
        <h1 className="page-title" style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <IndianRupee size={22} /> India GST Intelligence
        </h1>
        <p className="page-subtitle">
          The only platform that quantifies the invisible working capital cost of India's GST refund lag —
          per shipment, per carrier, per corridor.
        </p>
      </header>

      {/* Tabs */}
      <div style={{
        display: 'flex', gap: 4, marginBottom: 24,
        borderBottom: '1px solid rgba(255,255,255,0.1)', paddingBottom: 0,
      }}>
        {([
          { id: 'tracker',   label: 'Refund Tracker',       icon: <TrendingDown size={14} />,  badge: 'Demo Wedge' },
          { id: 'analyzer',  label: 'Per-Shipment Analyser', icon: <FileText size={14} />,     badge: null },
          { id: 'corridors', label: 'Trade Corridors',       icon: <Globe size={14} />,         badge: null },
        ] as const).map(({ id, label, icon, badge }) => (
          <button
            key={id}
            onClick={() => setActiveTab(id)}
            style={{
              padding: '9px 18px', borderRadius: '6px 6px 0 0', fontSize: 13, fontWeight: 600,
              display: 'flex', alignItems: 'center', gap: 7,
              background: activeTab === id ? 'rgba(99,102,241,0.15)' : 'transparent',
              color: activeTab === id ? 'var(--brand-primary, #6366f1)' : 'var(--text-secondary)',
              border: 'none', cursor: 'pointer',
              borderBottom: activeTab === id ? '2px solid var(--brand-primary, #6366f1)' : '2px solid transparent',
            }}
          >
            {icon} {label}
            {badge && (
              <span style={{
                fontSize: 9, fontWeight: 800, padding: '2px 6px', borderRadius: 3,
                background: 'rgba(239,68,68,0.2)', color: '#ef4444',
                textTransform: 'uppercase', letterSpacing: '0.05em',
              }}>{badge}</span>
            )}
          </button>
        ))}
      </div>

      {activeTab === 'tracker'   && <RefundTracker />}
      {activeTab === 'analyzer'  && <ShipmentAnalyser />}
      {activeTab === 'corridors' && <TradeCorridor />}
    </div>
  );
};

// ── Tab 1: Portfolio Refund Tracker (THE DEMO WEDGE) ─────────────────────────

const RefundTracker: React.FC = () => {
  const [shipments, setShipments] = useState<GSTShipmentInput[]>(SAMPLE_PORTFOLIO);
  const [wacc,      setWacc]      = useState(0.11);
  const [loading,   setLoading]   = useState(false);
  const [result,    setResult]    = useState<PortfolioSummary | null>(null);
  const [error,     setError]     = useState<string | null>(null);
  const [showEdit,  setShowEdit]  = useState(false);

  const run = async () => {
    setLoading(true); setError(null); setResult(null);
    try {
      const payload = { shipments: shipments.map(s => ({ ...s, wacc })), wacc, tenant_id: 'default_tenant' };
      const data = await apiService.getGSTRefundTracker(payload);
      setResult(data);
    } catch (e: any) {
      setError(e.message || 'GST tracker failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      {/* Hero */}
      {result && (
        <div style={{
          padding: '28px 32px', borderRadius: 12, marginBottom: 24,
          background: 'linear-gradient(135deg, rgba(239,68,68,0.1) 0%, rgba(245,158,11,0.07) 100%)',
          border: '1px solid rgba(239,68,68,0.3)',
        }}>
          <p style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 8, textTransform: 'uppercase', letterSpacing: '0.08em' }}>
            CFO Headline Number
          </p>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: 12, flexWrap: 'wrap' }}>
            <span style={{ fontSize: 36, fontWeight: 800, color: '#ef4444' }}>
              {fmt(result.total_working_capital_burn)}
            </span>
            <span style={{ fontSize: 15, color: 'var(--text-secondary)' }}>
              working capital cost from GST refund lag
            </span>
          </div>
          <p style={{ fontSize: 13, color: 'var(--text-secondary)', marginTop: 10 }}>
            You have <strong style={{ color: '#f59e0b' }}>{fmt(result.total_locked_inr)}</strong> locked
            in pending GST claims with the government — costing you{' '}
            <strong style={{ color: '#ef4444' }}>{fmt(result.daily_burn_inr)}/day</strong> at WACC {pct(result.wacc_used)}.
            {result.stuck_count > 0 && (
              <span style={{ color: '#ef4444' }}>
                {' '}{result.stuck_count} claim{result.stuck_count > 1 ? 's' : ''} are past the 60-day GSTN SLA — escalate immediately.
              </span>
            )}
          </p>
        </div>
      )}

      {/* KPI strip */}
      {result && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 14, marginBottom: 24 }}>
          {[
            { label: 'Total GST Locked',    value: fmt(result.total_locked_inr),           color: '#f59e0b' },
            { label: 'Working Capital Cost', value: fmt(result.total_working_capital_burn), color: '#ef4444' },
            { label: 'Projected Annual Burn',value: fmt(result.annual_burn_inr),            color: '#ef4444' },
            { label: 'Stuck Claims',         value: `${result.stuck_count} / ${result.claims?.length ?? 0}`,
              color: result.stuck_count > 0 ? '#ef4444' : '#4ade80' },
          ].map(({ label, value, color }) => (
            <div key={label} style={{
              padding: '14px 18px', borderRadius: 8,
              background: 'rgba(255,255,255,0.03)',
              border: `1px solid ${color}33`,
            }}>
              <p style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 6, textTransform: 'uppercase' }}>{label}</p>
              <p style={{ fontSize: 20, fontWeight: 700, margin: 0, color }}>{value}</p>
            </div>
          ))}
        </div>
      )}

      {/* Controls */}
      <div className="glass-panel" style={{ padding: 24, marginBottom: 20 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: showEdit ? 20 : 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
            <span style={{ fontSize: 13, fontWeight: 600 }}>
              {shipments.length} shipments loaded
            </span>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <label style={{ fontSize: 12, color: 'var(--text-secondary)' }}>WACC:</label>
              <input
                type="number" step="0.01" min="0.05" max="0.30"
                value={wacc}
                onChange={e => setWacc(Number(e.target.value))}
                style={{ width: 70, padding: '4px 8px', borderRadius: 5, border: '1px solid rgba(255,255,255,0.1)', background: 'rgba(255,255,255,0.04)', color: 'inherit', fontSize: 13 }}
              />
              <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>{pct(wacc)}</span>
            </div>
          </div>
          <div style={{ display: 'flex', gap: 10 }}>
            <button className="btn-secondary" onClick={() => setShowEdit(!showEdit)}
              style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12 }}>
              {showEdit ? <ChevronUp size={13} /> : <ChevronDown size={13} />} Edit Shipments
            </button>
            <button className="btn-primary" onClick={run} disabled={loading}
              style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              {loading ? <Loader2 size={14} className="animate-spin" /> : <RefreshCw size={14} />}
              {loading ? 'Calculating…' : 'Run GST Tracker'}
            </button>
          </div>
        </div>

        {/* Inline shipment editor */}
        {showEdit && (
          <div>
            <table style={{ width: '100%', fontSize: 12, borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.1)', color: 'var(--text-muted)', fontSize: 10, textTransform: 'uppercase' }}>
                  <th style={{ padding: '6px 10px', textAlign: 'left' }}>Shipment ID</th>
                  <th style={{ padding: '6px 10px', textAlign: 'left' }}>Route</th>
                  <th style={{ padding: '6px 10px', textAlign: 'left' }}>Order Value (₹)</th>
                  <th style={{ padding: '6px 10px', textAlign: 'left' }}>HS Chapter</th>
                  <th style={{ padding: '6px 10px', textAlign: 'left' }}>Refund Mode</th>
                </tr>
              </thead>
              <tbody>
                {shipments.map((s, i) => (
                  <tr key={i} style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                    <td style={{ padding: '4px 10px' }}><input value={s.shipment_id} onChange={e => { const n=[...shipments]; n[i]={...n[i],shipment_id:e.target.value}; setShipments(n); }} style={cellInput} /></td>
                    <td style={{ padding: '4px 10px' }}><input value={s.route} onChange={e => { const n=[...shipments]; n[i]={...n[i],route:e.target.value}; setShipments(n); }} style={cellInput} /></td>
                    <td style={{ padding: '4px 10px' }}><input type="number" value={s.order_value} onChange={e => { const n=[...shipments]; n[i]={...n[i],order_value:Number(e.target.value)}; setShipments(n); }} style={{...cellInput, width: 110}} /></td>
                    <td style={{ padding: '4px 10px' }}><input value={s.hs_code} onChange={e => { const n=[...shipments]; n[i]={...n[i],hs_code:e.target.value}; setShipments(n); }} style={{...cellInput, width: 70}} placeholder="84" /></td>
                    <td style={{ padding: '4px 10px' }}>
                      <select value={s.gst_refund_mode} onChange={e => { const n=[...shipments]; n[i]={...n[i],gst_refund_mode:e.target.value}; setShipments(n); }} style={{...cellInput, cursor:'pointer'}}>
                        {REFUND_MODES.map(m => <option key={m.value} value={m.value}>{m.label}</option>)}
                      </select>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            <button onClick={() => setShipments(s => [...s, { shipment_id: `EXP-${String(s.length+1).padStart(3,'0')}`, route: 'IN-US', order_value: 1000000, hs_code: '84', gst_refund_mode: 'auto' }])}
              style={{ marginTop: 10, fontSize: 12, color: 'var(--brand-primary)', background: 'none', border: 'none', cursor: 'pointer', padding: '4px 0' }}>
              + Add row
            </button>
          </div>
        )}
      </div>

      {error && <p style={{ color: '#ef4444', fontSize: 13, marginBottom: 16 }}>{error}</p>}

      {/* Recovery actions */}
      {result && result.stuck_count > 0 && (
        <div style={{ padding: '16px 20px', borderRadius: 8, background: 'rgba(239,68,68,0.07)', border: '1px solid rgba(239,68,68,0.25)', marginBottom: 20 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
            <AlertTriangle size={15} color="#ef4444" />
            <strong style={{ fontSize: 13 }}>Action Required — Stuck Claims</strong>
          </div>
          <ul style={{ margin: '0 0 0 20px', fontSize: 12, color: 'var(--text-secondary)', lineHeight: 1.8 }}>
            <li>File escalation with GSTN grievance portal under Form GST-PMT-09</li>
            <li>Engage CA to check GSTR-2B auto-population mismatches</li>
            <li>Verify IEC (Importer Exporter Code) is active on DGFT portal</li>
            <li>Check for RFD-01 rejection notices in GSTN inbox</li>
          </ul>
        </div>
      )}

      {!result && !loading && (
        <div style={{ padding: '20px', borderRadius: 8, background: 'rgba(99,102,241,0.06)', border: '1px solid rgba(99,102,241,0.2)', display: 'flex', alignItems: 'center', gap: 10 }}>
          <Info size={15} color="#6366f1" />
          <p style={{ fontSize: 13, margin: 0, color: 'var(--text-secondary)' }}>
            Pre-loaded with 5 sample shipments (pharma export, apparel export, machinery export, electronics import, machinery import).
            Click <strong>Run GST Tracker</strong> to compute the working capital burn.
          </p>
        </div>
      )}
    </div>
  );
};

// ── Tab 2: Per-Shipment Analyser ──────────────────────────────────────────────

const ShipmentAnalyser: React.FC = () => {
  const [form, setForm] = useState<GSTShipmentInput>({
    shipment_id: 'DEMO-001',
    route: 'IN-US',
    order_value: 5000000,
    hs_code: '30',
    gst_refund_mode: 'auto',
  });
  const [wacc,    setWacc]    = useState(0.11);
  const [loading, setLoading] = useState(false);
  const [result,  setResult]  = useState<GSTCostResult | null>(null);
  const [error,   setError]   = useState<string | null>(null);

  const run = async () => {
    setLoading(true); setError(null);
    try {
      const res = await apiService.getGSTCost([{ ...form, wacc }]);
      setResult(res[0]);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const isExport = form.route.startsWith('IN-') && !form.route.endsWith('-IN');

  return (
    <div>
      <div style={{ display: 'grid', gridTemplateColumns: '380px 1fr', gap: 24 }}>
        {/* Input form */}
        <div className="glass-panel" style={{ padding: 24 }}>
          <h3 style={{ fontSize: 14, fontWeight: 700, marginBottom: 20 }}>Shipment Details</h3>

          {[
            { label: 'Shipment / PO ID',   key: 'shipment_id', type: 'text',   placeholder: 'DEMO-001' },
            { label: 'Route',               key: 'route',       type: 'text',   placeholder: 'IN-US' },
            { label: 'Order Value (₹)',     key: 'order_value', type: 'number', placeholder: '5000000' },
            { label: 'HS Code (2 digits)',  key: 'hs_code',     type: 'text',   placeholder: '30 = Pharma' },
          ].map(({ label, key, type, placeholder }) => (
            <div key={key} style={{ marginBottom: 16 }}>
              <label style={{ fontSize: 12, color: 'var(--text-secondary)', display: 'block', marginBottom: 5 }}>{label}</label>
              <input
                type={type}
                placeholder={placeholder}
                value={(form as any)[key]}
                onChange={e => setForm(f => ({ ...f, [key]: type === 'number' ? Number(e.target.value) : e.target.value }))}
                style={inputStyle}
              />
            </div>
          ))}

          <div style={{ marginBottom: 16 }}>
            <label style={{ fontSize: 12, color: 'var(--text-secondary)', display: 'block', marginBottom: 5 }}>GST Refund Mode</label>
            <select value={form.gst_refund_mode} onChange={e => setForm(f => ({ ...f, gst_refund_mode: e.target.value }))} style={inputStyle}>
              {REFUND_MODES.map(m => <option key={m.value} value={m.value}>{m.label} — {m.desc}</option>)}
            </select>
          </div>

          <div style={{ marginBottom: 20 }}>
            <label style={{ fontSize: 12, color: 'var(--text-secondary)', display: 'block', marginBottom: 5 }}>WACC (e.g. 0.11 = 11%)</label>
            <input type="number" step="0.01" min="0.05" max="0.30" value={wacc} onChange={e => setWacc(Number(e.target.value))} style={inputStyle} />
          </div>

          <button className="btn-primary" onClick={run} disabled={loading} style={{ width: '100%', display: 'flex', justifyContent: 'center', alignItems: 'center', gap: 8 }}>
            {loading ? <Loader2 size={15} className="animate-spin" /> : <ArrowRight size={15} />}
            {loading ? 'Calculating…' : 'Calculate GST Impact'}
          </button>
          {error && <p style={{ marginTop: 12, fontSize: 12, color: '#ef4444' }}>{error}</p>}
        </div>

        {/* Results */}
        <div>
          {!result && !loading && (
            <div style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)', fontSize: 13 }}>
              Configure a shipment and click Calculate.
            </div>
          )}
          {loading && (
            <div style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 10 }}>
              <Loader2 size={24} className="animate-spin" style={{ color: '#6366f1' }} />
              <span style={{ fontSize: 13, color: 'var(--text-muted)' }}>Running GST compliance model…</span>
            </div>
          )}
          {result && !loading && (
            <div>
              {/* Direction badge */}
              <div style={{ marginBottom: 18, display: 'flex', alignItems: 'center', gap: 10 }}>
                <span style={{
                  fontSize: 11, fontWeight: 700, padding: '4px 12px', borderRadius: 4,
                  background: result.direction === 'export' ? 'rgba(74,222,128,0.15)' : 'rgba(96,165,250,0.15)',
                  color: result.direction === 'export' ? '#4ade80' : '#60a5fa',
                  border: `1px solid ${result.direction === 'export' ? 'rgba(74,222,128,0.3)' : 'rgba(96,165,250,0.3)'}`,
                  textTransform: 'uppercase',
                }}>
                  {result.direction}
                </span>
                <span style={{ fontSize: 13, color: 'var(--text-secondary)' }}>{result.route}</span>
              </div>

              {isExport && result.direction === 'export' ? (
                <ExportBreakdown r={result} />
              ) : (
                <ImportBreakdown r={result} />
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

const ExportBreakdown: React.FC<{ r: GSTCostResult }> = ({ r }) => (
  <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
    <ResultRow label="GST Rate on Product" value={pct(r.gst_rate ?? 0)} neutral />
    <ResultRow label="IGST Paid at Export" value={fmt(r.igst_paid ?? 0)} neutral />
    <ResultRow label="Refund Mode" value={r.refund_mode?.toUpperCase() ?? '—'} neutral />
    <ResultRow label="Refund Lag" value={r.refund_lag_days !== undefined ? `${r.refund_lag_days} days` : '—'} neutral />
    <ResultRow label="GST Working Capital Cost" value={fmt(r.gst_working_capital_cost ?? 0)} negative />
    <div style={{ borderTop: '1px solid rgba(255,255,255,0.1)', paddingTop: 10 }} />
    <ResultRow label="DGFT Drawback Rate (AIR)" value={pct(r.drawback_rate ?? 0)} neutral />
    <ResultRow label="Drawback Receivable" value={fmt(r.drawback_receivable ?? 0)} positive />
    <div style={{ borderTop: '1px solid rgba(255,255,255,0.1)', paddingTop: 10 }} />
    <ResultRow label="Net GST Impact on ReVM" value={fmt(r.net_gst_impact ?? 0)}
      negative={(r.net_gst_impact ?? 0) > 0} positive={(r.net_gst_impact ?? 0) <= 0} large />
    {(r.net_gst_impact ?? 0) <= 0 && (
      <div style={{ padding: '10px 14px', borderRadius: 6, background: 'rgba(74,222,128,0.08)', border: '1px solid rgba(74,222,128,0.2)', fontSize: 12, color: '#4ade80', display: 'flex', gap: 8 }}>
        <CheckCircle size={14} style={{ flexShrink: 0, marginTop: 1 }} />
        Drawback receivable exceeds refund cost — net positive cashflow. Register under LUT to eliminate the lag entirely.
      </div>
    )}
  </div>
);

const ImportBreakdown: React.FC<{ r: GSTCostResult }> = ({ r }) => (
  <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
    <ResultRow label="Basic Customs Duty Rate" value={pct(r.bcd_rate ?? 0)} neutral />
    <ResultRow label="BCD Cost (Sunk — Non-Recoverable)" value={fmt(r.bcd_cost ?? 0)} negative />
    <div style={{ borderTop: '1px solid rgba(255,255,255,0.1)', paddingTop: 10 }} />
    <ResultRow label="GST Rate (IGST at Customs)" value={pct(r.gst_rate ?? 0)} neutral />
    <ResultRow label="IGST Levied at Port" value={fmt(r.igst_on_import ?? 0)} neutral />
    <ResultRow label="ITC Recovery Lag" value="45 days (GSTR-2B)" neutral />
    <ResultRow label="ITC Working Capital Cost" value={fmt(r.itc_working_capital_cost ?? 0)} negative />
    <div style={{ borderTop: '1px solid rgba(255,255,255,0.1)', paddingTop: 10 }} />
    <ResultRow label="Total India Customs Cost on ReVM" value={fmt(r.total_india_customs_cost ?? 0)} negative large />
    <div style={{ padding: '10px 14px', borderRadius: 6, background: 'rgba(99,102,241,0.07)', border: '1px solid rgba(99,102,241,0.2)', fontSize: 12, color: 'var(--text-secondary)', display: 'flex', gap: 8 }}>
      <Info size={14} style={{ flexShrink: 0, marginTop: 1 }} color="#6366f1" />
      BCD is a sunk cost. IGST is recovered as ITC — only the working capital lag (45 days at WACC) is the true cost. Apply for EPCG scheme to reduce BCD on capital goods.
    </div>
  </div>
);

const ResultRow: React.FC<{
  label: string; value: string;
  positive?: boolean; negative?: boolean; neutral?: boolean; large?: boolean;
}> = ({ label, value, positive, negative, large }) => (
  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '8px 0' }}>
    <span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>{label}</span>
    <span style={{
      fontSize: large ? 18 : 13,
      fontWeight: large ? 800 : 600,
      color: positive ? '#4ade80' : negative ? '#ef4444' : 'inherit',
    }}>{value}</span>
  </div>
);

// ── Tab 3: Trade Corridors ────────────────────────────────────────────────────

const TradeCorridor: React.FC = () => {
  const { data, isLoading, error } = useIndiaRoutes();

  if (isLoading) return (
    <div style={{ display: 'flex', gap: 10, alignItems: 'center', padding: 40, color: 'var(--text-muted)' }}>
      <Loader2 size={20} className="animate-spin" /> Loading corridors…
    </div>
  );
  if (error || !data) return <p style={{ color: '#ef4444', fontSize: 13 }}>Failed to load corridor data.</p>;

  const corridors: Record<string, any> = data.corridors ?? {};
  const exports = Object.entries(corridors).filter(([, v]) => v.direction === 'export');
  const imports = Object.entries(corridors).filter(([, v]) => v.direction === 'import');

  return (
    <div>
      {/* Notes */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 14, marginBottom: 28 }}>
        {[
          { label: 'GST Treatment on Exports', text: data.gst_note },
          { label: 'DGFT Drawback',             text: data.drawback_note },
          { label: 'Working Capital Costing',   text: data.wacc_note },
        ].map(({ label, text }) => (
          <div key={label} style={{ padding: '14px 16px', borderRadius: 8, background: 'rgba(99,102,241,0.06)', border: '1px solid rgba(99,102,241,0.15)', fontSize: 12 }}>
            <p style={{ fontWeight: 700, fontSize: 11, textTransform: 'uppercase', color: '#6366f1', marginBottom: 6 }}>{label}</p>
            <p style={{ color: 'var(--text-secondary)', margin: 0, lineHeight: 1.6 }}>{text}</p>
          </div>
        ))}
      </div>

      {/* Export corridors */}
      <h3 style={{ fontSize: 13, fontWeight: 700, marginBottom: 14, color: '#4ade80', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Export Corridors (India → World)</h3>
      <CorridorTable rows={exports} type="export" />

      {/* Import corridors */}
      <h3 style={{ fontSize: 13, fontWeight: 700, margin: '28px 0 14px', color: '#60a5fa', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Import Corridors (World → India)</h3>
      <CorridorTable rows={imports} type="import" />
    </div>
  );
};

const CorridorTable: React.FC<{ rows: [string, any][]; type: 'export' | 'import' }> = ({ rows, type }) => (
  <div className="glass-panel" style={{ padding: 0, marginBottom: 8, overflow: 'hidden' }}>
    <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
      <thead>
        <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.1)', color: 'var(--text-muted)', fontSize: 10, textTransform: 'uppercase' }}>
          <th style={{ padding: '10px 16px', textAlign: 'left' }}>Corridor</th>
          <th style={{ padding: '10px 16px', textAlign: 'left' }}>{type === 'export' ? 'Destination' : 'Origin'}</th>
          <th style={{ padding: '10px 16px', textAlign: 'left' }}>{type === 'export' ? 'Dest. Import Duty' : 'India BCD Rate'}</th>
          <th style={{ padding: '10px 16px', textAlign: 'left' }}>FTA / Agreement</th>
          <th style={{ padding: '10px 16px', textAlign: 'left' }}>{type === 'export' ? 'DGFT Drawback' : 'ITC Recoverable'}</th>
          <th style={{ padding: '10px 16px', textAlign: 'left' }}>Notes</th>
        </tr>
      </thead>
      <tbody>
        {rows.map(([code, v]) => (
          <tr key={code} style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
            <td style={{ padding: '10px 16px', fontWeight: 700, fontFamily: 'monospace' }}>{code}</td>
            <td style={{ padding: '10px 16px', color: 'var(--text-secondary)' }}>{v.destination ?? v.origin}</td>
            <td style={{ padding: '10px 16px', fontWeight: 700 }}>
              {pct(type === 'export' ? (v.import_duty ?? 0) : (v.bcd_rate ?? 0))}
            </td>
            <td style={{ padding: '10px 16px', color: 'var(--text-secondary)', fontSize: 11 }}>{v.fta || '—'}</td>
            <td style={{ padding: '10px 16px' }}>
              {(type === 'export' ? v.dgft_drawback : v.itc_recoverable)
                ? <CheckCircle size={14} color="#4ade80" />
                : <span style={{ color: 'var(--text-muted)' }}>—</span>}
            </td>
            <td style={{ padding: '10px 16px', color: 'var(--text-muted)', fontSize: 11, maxWidth: 260 }}>{v.notes || '—'}</td>
          </tr>
        ))}
      </tbody>
    </table>
  </div>
);

// ── Shared styles ─────────────────────────────────────────────────────────────

const inputStyle: React.CSSProperties = {
  width: '100%', padding: '8px 12px', borderRadius: 6,
  border: '1px solid rgba(255,255,255,0.12)',
  background: 'rgba(255,255,255,0.04)',
  color: 'inherit', fontSize: 13, outline: 'none',
};

const cellInput: React.CSSProperties = {
  padding: '4px 8px', borderRadius: 4, fontSize: 11,
  border: '1px solid rgba(255,255,255,0.1)',
  background: 'rgba(255,255,255,0.04)',
  color: 'inherit', width: '100%', outline: 'none',
};

export default GSTDashboard;
