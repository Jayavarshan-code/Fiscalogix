import React, { useState } from 'react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  AreaChart, Area, ReferenceLine, Cell, Legend,
  RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis,
} from 'recharts';
import {
  Loader2, Zap, CheckCircle, AlertTriangle, ChevronDown, ChevronUp, Clock, Terminal,
  ArrowLeft, Network, Package, TrendingUp, BarChart3, Layers,
} from 'lucide-react';
import { apiService } from '../../services/api';

// ── helpers ───────────────────────────────────────────────────────────────────

const fmt$ = (v: number | null | undefined) => {
  const n = Number.isFinite(v as number) ? (v as number) : 0;
  if (Math.abs(n) >= 1e6) return `$${(n / 1e6).toFixed(2)}M`;
  if (Math.abs(n) >= 1e3) return `$${(n / 1e3).toFixed(1)}k`;
  return `$${n.toLocaleString()}`;
};
const pct = (v: number) => `${(v * 100).toFixed(1)}%`;

function normPDF(x: number, mean: number, std: number) {
  return (1 / (std * Math.sqrt(2 * Math.PI))) * Math.exp(-0.5 * ((x - mean) / std) ** 2);
}

// ── shared UI ─────────────────────────────────────────────────────────────────

const Section: React.FC<{ title: string; sub: string; badge?: string; children: React.ReactNode }> = ({
  title, sub, badge, children,
}) => {
  const [open, setOpen] = useState(true);
  return (
    <div className="glass-panel p-5 mb-6 rounded-2xl border border-subtle">
      <button className="flex justify-between items-center w-full mb-4" onClick={() => setOpen(!open)}>
        <div className="text-left flex items-center gap-3">
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-sm font-black text-primary uppercase tracking-tight">{title}</h3>
              {badge && (
                <span className="text-[8px] font-black px-2 py-0.5 bg-brand-primary/10 text-brand-primary rounded-full border border-brand-primary/30 uppercase">
                  {badge}
                </span>
              )}
            </div>
            <p className="text-[10px] text-muted mt-0.5">{sub}</p>
          </div>
        </div>
        {open ? <ChevronUp size={16} className="text-muted shrink-0" /> : <ChevronDown size={16} className="text-muted shrink-0" />}
      </button>
      {open && children}
    </div>
  );
};

const Err: React.FC<{ msg: string }> = ({ msg }) => (
  <div className="mt-3 flex items-center gap-2 text-critical text-[11px] p-3 bg-critical/10 rounded-xl border border-critical/30">
    <AlertTriangle size={14} /> {msg}
  </div>
);

const StatBox: React.FC<{ label: string; value: React.ReactNode; sub?: string; color?: string }> = ({
  label, value, sub, color = 'text-primary',
}) => (
  <div className="p-3 bg-surface rounded-xl border border-subtle">
    <div className="text-[9px] font-bold text-muted uppercase mb-1">{label}</div>
    <div className={`text-lg font-black ${color}`}>{value}</div>
    {sub && <div className="text-[9px] text-muted mt-0.5">{sub}</div>}
  </div>
);

// ── JobPoller ─────────────────────────────────────────────────────────────────

type JobResponse =
  | { status: 'accepted'; job_id: string }
  | { status: 'completed'; job_id: null; result: any };

type PollState = 'polling' | 'completed' | 'failed' | 'timeout';

const JobPoller: React.FC<{
  response: JobResponse;
  resultRenderer: (result: any) => React.ReactNode;
}> = ({ response, resultRenderer }) => {
  const [pollState, setPollState] = useState<PollState>(
    response.status === 'completed' ? 'completed' : 'polling',
  );
  const [result, setResult] = useState<any>(response.status === 'completed' ? response.result : null);
  const [error, setError]   = useState('');
  const [elapsed, setElapsed] = useState(0);

  React.useEffect(() => {
    if (response.status === 'completed') return;
    const start = Date.now();
    const iv = setInterval(async () => {
      const secs = Math.floor((Date.now() - start) / 1000);
      setElapsed(secs);
      if (secs > 90) { clearInterval(iv); setPollState('timeout'); return; }
      try {
        const data = await apiService.getJobStatus(response.job_id);
        if (data.status === 'COMPLETED') { clearInterval(iv); setResult(data.result); setPollState('completed'); }
        else if (data.status === 'FAILED') { clearInterval(iv); setError(data.error || 'Job failed'); setPollState('failed'); }
      } catch (e: any) { clearInterval(iv); setError(e.message); setPollState('failed'); }
    }, 2000);
    return () => clearInterval(iv);
  }, [response]);

  if (pollState === 'polling') return (
    <div className="mt-3 p-3 bg-surface border border-subtle rounded-xl flex items-center gap-3">
      <Loader2 size={14} className="animate-spin text-brand-primary shrink-0" />
      <div>
        <div className="text-[10px] font-black text-primary">Running in background…</div>
        <div className="text-[9px] text-muted font-mono mt-0.5">{response.job_id} · {elapsed}s</div>
      </div>
    </div>
  );
  if (pollState === 'timeout') return (
    <div className="mt-3 p-4 bg-warning/5 border border-warning/30 rounded-xl">
      <div className="text-[10px] font-black text-warning mb-1 flex items-center gap-2">
        <Clock size={12} /> Worker timeout after 90s
      </div>
      <div className="text-[9px] text-muted font-mono mb-2">{response.job_id}</div>
      <div className="flex items-start gap-2 text-[10px] text-secondary">
        <Terminal size={10} className="mt-0.5 shrink-0" />
        Start Celery: <code className="font-mono ml-1">celery -A app.celery_app worker --loglevel=info</code>
      </div>
    </div>
  );
  if (pollState === 'failed') return <Err msg={error} />;
  return (
    <div className="mt-3">
      <div className="flex items-center gap-2 text-[9px] font-black text-safe uppercase mb-2">
        <CheckCircle size={11} />
        {response.job_id ? `Completed · Job ${response.job_id}` : 'Completed · Inline execution'}
      </div>
      {resultRenderer(result)}
    </div>
  );
};

// ── 1. DELAY PREDICTION ───────────────────────────────────────────────────────

const RISK_COLORS: Record<string, string> = {
  CRITICAL: '#ef4444',
  DELAYED:  '#f97316',
  MODERATE: '#eab308',
  ON_TRACK: '#22c55e',
};

function delayLabel(d: number) {
  if (d > 4) return 'CRITICAL';
  if (d > 2) return 'DELAYED';
  if (d > 0.5) return 'MODERATE';
  return 'ON TRACK';
}

const DEMO_ROWS = [
  { shipment_id: 'SYS-1001', route: 'CN-US', order_value: 500000, credit_days: 30, carrier: 'COSCO' },
  { shipment_id: 'SYS-1002', route: 'EU-US', order_value: 210000, credit_days: 45, carrier: 'Maersk' },
  { shipment_id: 'SYS-1003', route: 'IN-AE', order_value: 85000,  credit_days: 30, carrier: 'MSC' },
];

const DelayPredictionPanel: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [result, setResult]   = useState<any>(null);
  const [error, setError]     = useState('');

  const run = async () => {
    setLoading(true); setError(''); setResult(null);
    try { setResult(await apiService.predictDelay(DEMO_ROWS)); }
    catch (e: any) { setError(e.message); }
    finally { setLoading(false); }
  };

  const predictions: any[] = result?.predictions ?? [];
  const avgDelay = predictions.length
    ? predictions.reduce((s: number, p: any) => s + p.predicted_delay_days, 0) / predictions.length
    : 0;
  const totalImpact = predictions.reduce((s: number, p: any) => {
    const row = DEMO_ROWS.find(r => r.shipment_id === p.shipment_id);
    return s + p.predicted_delay_days * (row?.order_value ?? 0) * 0.005;
  }, 0);

  return (
    <Section title="Batch Delay Prediction" sub="POST /api/v1/predict/delay — XGBoost regressor across shipment portfolio" badge="ML">
      <div className="overflow-x-auto mb-3">
        <table className="w-full text-[10px]">
          <thead>
            <tr className="text-muted text-[9px] uppercase border-b border-subtle">
              <th className="text-left pb-2 pr-3">Shipment</th>
              <th className="text-left pb-2 pr-3">Route</th>
              <th className="text-right pb-2 pr-3">Value</th>
              <th className="text-right pb-2">Credit Days</th>
            </tr>
          </thead>
          <tbody>
            {DEMO_ROWS.map((r) => (
              <tr key={r.shipment_id} className="border-b border-subtle/30">
                <td className="py-1.5 pr-3 font-mono text-primary">{r.shipment_id}</td>
                <td className="pr-3 text-secondary">{r.route}</td>
                <td className="pr-3 text-right">{fmt$(r.order_value)}</td>
                <td className="text-right text-secondary">{r.credit_days}d</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <button className="btn-primary text-xs flex items-center gap-2" onClick={run} disabled={loading}>
        {loading ? <Loader2 size={12} className="animate-spin" /> : <Zap size={12} />}
        Predict Delay for {DEMO_ROWS.length} Shipments
      </button>

      {result && (
        <div className="mt-4 space-y-4">
          <div className="grid grid-cols-3 gap-2">
            <StatBox label="Model Version" value={result.model_version ?? '—'} />
            <StatBox
              label="Avg Predicted Delay"
              value={`+${avgDelay.toFixed(1)}d`}
              color={avgDelay > 2 ? 'text-critical' : 'text-safe'}
            />
            <StatBox
              label="Est. Financial Impact"
              value={fmt$(totalImpact)}
              sub="delay penalty @ 0.5%/day"
              color="text-warning"
            />
          </div>

          <div className="space-y-3">
            {predictions.map((p: any) => {
              const label = delayLabel(p.predicted_delay_days);
              const color = RISK_COLORS[label] ?? '#94a3b8';
              const row   = DEMO_ROWS.find(r => r.shipment_id === p.shipment_id);
              const impact = p.predicted_delay_days * (row?.order_value ?? 0) * 0.005;
              const barPct = Math.min(100, (p.predicted_delay_days / 7) * 100);
              return (
                <div key={p.shipment_id} className="p-3 bg-surface rounded-xl border border-subtle">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-[10px] font-mono font-black text-primary">{p.shipment_id}</span>
                    <span
                      className="text-[9px] font-black px-2 py-0.5 rounded-full"
                      style={{ background: color + '22', color }}
                    >
                      {label}
                    </span>
                  </div>
                  <div className="h-2 rounded-full bg-subtle mb-2 overflow-hidden">
                    <div
                      className="h-full rounded-full transition-all"
                      style={{ width: `${barPct}%`, background: color }}
                    />
                  </div>
                  <div className="flex justify-between text-[9px] text-muted">
                    <span>Predicted delay: <strong style={{ color }}>{p.predicted_delay_days > 0 ? `+${p.predicted_delay_days.toFixed(1)}d` : 'On time'}</strong></span>
                    <span>Impact: <strong className="text-warning">{fmt$(impact)}</strong></span>
                  </div>
                </div>
              );
            })}
          </div>

          {predictions.length > 0 && (
            <div>
              <div className="text-[9px] font-bold text-muted uppercase mb-2">Delay Days by Shipment</div>
              <ResponsiveContainer width="100%" height={140}>
                <BarChart data={predictions} margin={{ top: 4, right: 8, left: -20, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="rgba(255,255,255,0.06)" />
                  <XAxis dataKey="shipment_id" tick={{ fontSize: 9, fill: '#64748b' }} axisLine={false} tickLine={false} />
                  <YAxis tick={{ fontSize: 9, fill: '#64748b' }} axisLine={false} tickLine={false} unit="d" />
                  <Tooltip
                    contentStyle={{ fontSize: 10, borderRadius: 6 }}
                    formatter={(v: any) => [`+${Number(v).toFixed(1)}d`, 'Predicted Delay']}
                  />
                  <Bar dataKey="predicted_delay_days" radius={[4, 4, 0, 0]}>
                    {predictions.map((p: any) => (
                      <Cell key={p.shipment_id} fill={RISK_COLORS[delayLabel(p.predicted_delay_days)]} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>
      )}
      {error && <Err msg={error} />}
    </Section>
  );
};

// ── 2. EFI PORTFOLIO OPTIMIZER ────────────────────────────────────────────────

const CANDIDATE_MATRIX = [
  [
    { shipment_id: 'SYS-1001', action_name: 'HOLD',         simulated_efi: 12400, total_cost: 0     },
    { shipment_id: 'SYS-1001', action_name: 'REROUTE_AIR',  simulated_efi: 18200, total_cost: 14000 },
    { shipment_id: 'SYS-1001', action_name: 'REROUTE_RAIL', simulated_efi: 15100, total_cost: 5200  },
  ],
  [
    { shipment_id: 'SYS-1002', action_name: 'HOLD',         simulated_efi: 8200,  total_cost: 0    },
    { shipment_id: 'SYS-1002', action_name: 'EXPEDITE',     simulated_efi: 11600, total_cost: 8800 },
    { shipment_id: 'SYS-1002', action_name: 'REROUTE_RAIL', simulated_efi: 9800,  total_cost: 3100 },
  ],
];

const EFIOptimizerPanel: React.FC = () => {
  const [loading, setLoading]     = useState(false);
  const [result, setResult]       = useState<any>(null);
  const [error, setError]         = useState('');
  const [riskAppetite, setRiskAppetite] = useState('BALANCED');
  const [availableCash, setAvailableCash] = useState(1000000);

  const run = async () => {
    setLoading(true); setError(''); setResult(null);
    try { setResult(await apiService.optimizeEFI(CANDIDATE_MATRIX, availableCash, riskAppetite)); }
    catch (e: any) { setError(e.message); }
    finally { setLoading(false); }
  };

  const decisions: any[] = result?.optimized_decisions ?? [];
  const usedCash = decisions.reduce((s: number, d: any) => {
    const actions = CANDIDATE_MATRIX.flat().filter(a => a.shipment_id === d.shipment_id && a.action_name === d.action);
    return s + (actions[0]?.total_cost ?? 0);
  }, 0);
  const budgetPct = Math.min(100, (usedCash / availableCash) * 100);

  const chartData = CANDIDATE_MATRIX.map(actions => ({
    shipment: actions[0].shipment_id,
    ...Object.fromEntries(actions.map(a => [a.action_name, a.simulated_efi])),
  }));
  const actionKeys = [...new Set(CANDIDATE_MATRIX.flat().map(a => a.action_name))];
  const ACTION_COLORS = ['#3b82f6', '#22c55e', '#f59e0b', '#ef4444'];

  return (
    <Section title="EFI Portfolio Optimizer (StochasticMIP)" sub="POST /api/v1/predict/efi — Optimal action set under budget + CVaR constraint" badge="MIP">
      <div className="flex gap-4 mb-4">
        <div>
          <label className="text-[9px] font-bold text-muted uppercase block mb-1">Risk Appetite</label>
          <select
            className="bg-surface border border-subtle rounded-lg px-3 py-2 text-xs text-primary"
            value={riskAppetite} onChange={e => setRiskAppetite(e.target.value)}
          >
            <option>CONSERVATIVE</option>
            <option>BALANCED</option>
            <option>AGGRESSIVE</option>
          </select>
        </div>
        <div>
          <label className="text-[9px] font-bold text-muted uppercase block mb-1">Cash Budget ($)</label>
          <input
            type="number" step="100000"
            className="bg-surface border border-subtle rounded-lg px-3 py-2 text-xs text-primary w-32"
            value={availableCash} onChange={e => setAvailableCash(parseInt(e.target.value))}
          />
        </div>
      </div>

      <div className="mb-4">
        <div className="text-[9px] font-bold text-muted uppercase mb-2">Candidate Actions — EFI per Shipment</div>
        <ResponsiveContainer width="100%" height={160}>
          <BarChart data={chartData} margin={{ top: 4, right: 8, left: -10, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="rgba(255,255,255,0.06)" />
            <XAxis dataKey="shipment" tick={{ fontSize: 9, fill: '#64748b' }} axisLine={false} tickLine={false} />
            <YAxis tick={{ fontSize: 9, fill: '#64748b' }} axisLine={false} tickLine={false} tickFormatter={v => `$${v / 1000}k`} />
            <Tooltip contentStyle={{ fontSize: 10, borderRadius: 6 }} formatter={(v: any) => [fmt$(v), '']} />
            <Legend iconSize={8} wrapperStyle={{ fontSize: 9 }} />
            {actionKeys.map((key, i) => (
              <Bar key={key} dataKey={key} fill={ACTION_COLORS[i % ACTION_COLORS.length]} radius={[3, 3, 0, 0]} />
            ))}
          </BarChart>
        </ResponsiveContainer>
      </div>

      <button className="btn-primary text-xs flex items-center gap-2" onClick={run} disabled={loading}>
        {loading ? <Loader2 size={12} className="animate-spin" /> : <Zap size={12} />}
        Optimize Portfolio ({riskAppetite})
      </button>

      {result && (
        <div className="mt-4 space-y-4">
          <div>
            <div className="flex justify-between text-[9px] text-muted mb-1">
              <span>Budget utilization</span>
              <span className="font-mono">{fmt$(usedCash)} / {fmt$(availableCash)} ({budgetPct.toFixed(0)}%)</span>
            </div>
            <div className="h-2 rounded-full bg-subtle overflow-hidden">
              <div
                className="h-full rounded-full transition-all"
                style={{
                  width: `${budgetPct}%`,
                  background: budgetPct > 90 ? '#ef4444' : budgetPct > 70 ? '#f59e0b' : '#22c55e',
                }}
              />
            </div>
          </div>

          {decisions.map((d: any, i: number) => {
            const holdEFI = CANDIDATE_MATRIX.flat().find(
              a => a.shipment_id === d.shipment_id && a.action_name === 'HOLD',
            )?.simulated_efi ?? 0;
            const roi = d.action !== 'HOLD' && (CANDIDATE_MATRIX.flat().find(a => a.shipment_id === d.shipment_id && a.action_name === d.action)?.total_cost ?? 0) > 0
              ? ((d.expected_efi - holdEFI) / (CANDIDATE_MATRIX.flat().find(a => a.shipment_id === d.shipment_id && a.action_name === d.action)?.total_cost ?? 1) * 100).toFixed(0)
              : null;
            return (
              <div key={i} className="p-4 bg-surface rounded-xl border border-subtle">
                <div className="flex items-start justify-between mb-3">
                  <div>
                    <div className="text-[10px] font-mono font-black text-primary">{d.shipment_id}</div>
                    <div className="text-base font-black text-brand-primary mt-0.5">{d.action}</div>
                  </div>
                  <div className="text-right">
                    <div className="text-[9px] text-muted">EFI Score</div>
                    <div className="text-base font-black text-safe">{fmt$(d.expected_efi)}</div>
                    {d.robust_efi_floor && (
                      <div className="text-[9px] text-muted">Floor (CVaR): {fmt$(d.robust_efi_floor)}</div>
                    )}
                  </div>
                </div>
                <div className="grid grid-cols-3 gap-2 mb-3 text-[10px]">
                  <div className="p-2 rounded-lg bg-subtle/40">
                    <div className="text-muted text-[9px]">Confidence</div>
                    <div className="font-black">{d.confidence_score ? pct(d.confidence_score) : '—'}</div>
                  </div>
                  <div className="p-2 rounded-lg bg-subtle/40">
                    <div className="text-muted text-[9px]">Profit Delta vs Hold</div>
                    <div className={`font-black ${(d.executive_summary?.profit_impact_delta ?? 0) >= 0 ? 'text-safe' : 'text-critical'}`}>
                      {d.executive_summary?.profit_impact_delta != null ? fmt$(d.executive_summary.profit_impact_delta) : '—'}
                    </div>
                  </div>
                  <div className="p-2 rounded-lg bg-subtle/40">
                    <div className="text-muted text-[9px]">ROI on Action Cost</div>
                    <div className="font-black text-brand-primary">{roi ? `${roi}%` : '∞ (no cost)'}</div>
                  </div>
                </div>
                {d.executive_summary?.executive_narrative && (
                  <p className="text-[10px] text-secondary italic border-l-2 border-brand-primary/40 pl-2">
                    {d.executive_summary.executive_narrative}
                  </p>
                )}
                {d.executive_summary?.operational_alert && (
                  <div className="mt-2 text-[9px] font-bold text-warning">{d.executive_summary.operational_alert}</div>
                )}
                {d.tight_constraints?.length > 0 && (
                  <div className="mt-2 text-[9px] text-critical bg-critical/10 rounded-lg px-2 py-1">
                    ⚠ {d.tight_constraints.join(' | ')}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
      {error && <Err msg={error} />}
    </Section>
  );
};

// ── 3. MILP NETWORK OPTIMIZER ─────────────────────────────────────────────────

const NETWORK_PAYLOAD = {
  origins:      ['Shanghai', 'Rotterdam'],
  destinations: ['Los Angeles', 'New York'],
  supply:       { Shanghai: 1200, Rotterdam: 800 },
  demand:       { 'Los Angeles': 900, 'New York': 1100 },
  costs: {
    Shanghai:  { 'Los Angeles': 1850, 'New York': 2100 },
    Rotterdam: { 'Los Angeles': 2300, 'New York': 1650 },
  },
  capacities: {
    Shanghai:  { 'Los Angeles': 1000, 'New York': 800 },
    Rotterdam: { 'Los Angeles': 700,  'New York': 900 },
  },
};

const NetworkResult: React.FC<{ result: any }> = ({ result }) => {
  const plan: any[] = result?.routing_plan ?? [];

  const naiveCost = Object.keys(NETWORK_PAYLOAD.demand).reduce((sum, dest) => {
    const cheapest = Object.keys(NETWORK_PAYLOAD.costs).reduce((best, orig) => {
      const c = NETWORK_PAYLOAD.costs[orig as 'Shanghai' | 'Rotterdam'][dest as 'Los Angeles' | 'New York'];
      return c < best ? c : best;
    }, Infinity);
    return sum + cheapest * NETWORK_PAYLOAD.demand[dest as 'Los Angeles' | 'New York'];
  }, 0);
  const savings = naiveCost - (result?.total_cost_usd ?? 0);

  const utilChart = plan.map(r => ({
    lane: `${r.origin.split(' ')[0]}→${r.destination.split(' ')[0]}`,
    shipped: r.quantity,
    capacity: NETWORK_PAYLOAD.capacities[r.origin as 'Shanghai' | 'Rotterdam']?.[r.destination as 'Los Angeles' | 'New York'] ?? r.quantity,
    cost: r.total_lane_cost,
  })).map(r => ({ ...r, utilPct: Math.round((r.shipped / r.capacity) * 100) }));

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-3 gap-2">
        <StatBox label="Optimal Total Cost" value={fmt$(result?.total_cost_usd)} color="text-safe" />
        <StatBox label="Solver Status" value={result?.optimization_status ?? 'Optimal'} />
        <StatBox label="Savings vs Naïve" value={fmt$(savings)} sub="without capacity-aware routing" color="text-brand-primary" />
      </div>

      {plan.length > 0 && (
        <>
          <div className="text-[9px] font-bold text-muted uppercase">Lane Cost Breakdown</div>
          <ResponsiveContainer width="100%" height={160}>
            <BarChart data={utilChart} margin={{ top: 4, right: 8, left: -10, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="rgba(255,255,255,0.06)" />
              <XAxis dataKey="lane" tick={{ fontSize: 9, fill: '#64748b' }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fontSize: 9, fill: '#64748b' }} axisLine={false} tickLine={false} tickFormatter={v => `$${v / 1000}k`} />
              <Tooltip contentStyle={{ fontSize: 10, borderRadius: 6 }} formatter={(v: any) => [fmt$(v), 'Lane Cost']} />
              <Bar dataKey="cost" fill="#3b82f6" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>

          <div>
            <div className="text-[9px] font-bold text-muted uppercase mb-2">Capacity Utilization per Lane</div>
            <div className="space-y-2">
              {utilChart.map(r => (
                <div key={r.lane}>
                  <div className="flex justify-between text-[9px] text-muted mb-0.5">
                    <span className="font-mono font-black text-primary">{r.lane}</span>
                    <span>{r.shipped} / {r.capacity} FEU — {r.utilPct}%</span>
                  </div>
                  <div className="h-1.5 rounded-full bg-subtle overflow-hidden">
                    <div
                      className="h-full rounded-full"
                      style={{
                        width: `${r.utilPct}%`,
                        background: r.utilPct > 90 ? '#ef4444' : r.utilPct > 70 ? '#f59e0b' : '#22c55e',
                      }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-[10px]">
              <thead>
                <tr className="text-[9px] text-muted uppercase border-b border-subtle">
                  <th className="text-left pb-2 pr-3">Origin</th>
                  <th className="text-left pb-2 pr-3">Destination</th>
                  <th className="text-right pb-2 pr-3">Qty (FEU)</th>
                  <th className="text-right pb-2 pr-3">Unit Cost</th>
                  <th className="text-right pb-2">Lane Total</th>
                </tr>
              </thead>
              <tbody>
                {plan.map((r: any, i: number) => (
                  <tr key={i} className="border-b border-subtle/30">
                    <td className="py-1.5 pr-3 font-mono text-primary">{r.origin}</td>
                    <td className="pr-3 text-secondary">{r.destination}</td>
                    <td className="pr-3 text-right font-mono">{r.quantity}</td>
                    <td className="pr-3 text-right font-mono text-muted">${r.unit_cost?.toLocaleString()}</td>
                    <td className="text-right font-mono text-safe">{fmt$(r.total_lane_cost)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
};

const NetworkOptimizerPanel: React.FC = () => {
  const [loading, setLoading]   = useState(false);
  const [response, setResponse] = useState<JobResponse | null>(null);
  const [error, setError]       = useState('');

  const run = async () => {
    setLoading(true); setError(''); setResponse(null);
    try { setResponse(await apiService.optimizeNetwork(NETWORK_PAYLOAD) as JobResponse); }
    catch (e: any) { setError(e.message); }
    finally { setLoading(false); }
  };

  return (
    <Section title="MILP Network Routing Optimizer" sub="POST /optimization/network — Min-cost flow with capacity constraints (PuLP/CBC)" badge="MILP">
      <div className="mb-4 text-[10px] text-secondary grid grid-cols-2 gap-4">
        <div>
          <div className="text-[9px] font-bold text-muted uppercase mb-1">Origins → Supply (FEU)</div>
          {Object.entries(NETWORK_PAYLOAD.supply).map(([k, v]) => (
            <div key={k} className="flex justify-between py-0.5"><span>{k}</span><span className="font-mono">{v}</span></div>
          ))}
        </div>
        <div>
          <div className="text-[9px] font-bold text-muted uppercase mb-1">Destinations → Demand (FEU)</div>
          {Object.entries(NETWORK_PAYLOAD.demand).map(([k, v]) => (
            <div key={k} className="flex justify-between py-0.5"><span>{k}</span><span className="font-mono">{v}</span></div>
          ))}
        </div>
      </div>
      <button className="btn-primary text-xs flex items-center gap-2" onClick={run} disabled={loading}>
        {loading ? <Loader2 size={12} className="animate-spin" /> : <Zap size={12} />}
        Dispatch to MILP Solver
      </button>
      {response && <JobPoller response={response} resultRenderer={r => <NetworkResult result={r} />} />}
      {error && <Err msg={error} />}
    </Section>
  );
};

// ── 4. MONTE CARLO ────────────────────────────────────────────────────────────

const MC_LEGS = [
  { mean_days: 14.0, std_days: 2.5, cost_per_day: 3200, label: 'Ocean Freight' },
  { mean_days: 3.0,  std_days: 1.0, cost_per_day: 850,  label: 'Port Dwell'    },
  { mean_days: 2.0,  std_days: 0.5, cost_per_day: 420,  label: 'Last Mile'     },
];

function buildDistributionCurve(legs: typeof MC_LEGS, targetDays: number) {
  const totalMean = legs.reduce((s, l) => s + l.mean_days, 0);
  const totalStd  = Math.sqrt(legs.reduce((s, l) => s + l.std_days ** 2, 0));
  const lo = totalMean - 3.5 * totalStd;
  const hi = totalMean + 3.5 * totalStd;
  const steps = 60;
  const points = [];
  for (let i = 0; i <= steps; i++) {
    const x = lo + (hi - lo) * (i / steps);
    points.push({
      days: parseFloat(x.toFixed(1)),
      density: normPDF(x, totalMean, totalStd),
      onTime: x <= targetDays ? normPDF(x, totalMean, totalStd) : 0,
      late:   x >  targetDays ? normPDF(x, totalMean, totalStd) : 0,
    });
  }
  return { points, totalMean, totalStd };
}

function sensitivityRows(legs: typeof MC_LEGS, targetDays: number, baseProb: number) {
  return legs.map((leg, i) => {
    const shifted = legs.map((l, j) => j === i ? { ...l, mean_days: l.mean_days + 2 } : l);
    const newMean = shifted.reduce((s, l) => s + l.mean_days, 0);
    const std     = Math.sqrt(shifted.reduce((s, l) => s + l.std_days ** 2, 0));
    const z = (targetDays - newMean) / std;
    const t = 1 / (1 + 0.2316419 * Math.abs(z));
    const poly = t * (0.319381530 + t * (-0.356563782 + t * (1.781477937 + t * (-1.821255978 + t * 1.330274429))));
    const cdf = z >= 0 ? 1 - normPDF(z, 0, 1) * poly : normPDF(z, 0, 1) * poly;
    return {
      leg: leg.label,
      newProb: parseFloat(cdf.toFixed(4)),
      delta: parseFloat((cdf - baseProb).toFixed(4)),
    };
  });
}

const MonteCarloResult: React.FC<{ result: any; legs: typeof MC_LEGS; targetDays: number }> = ({
  result, legs, targetDays,
}) => {
  const prob   = result?.probability_on_time ?? 0;
  const p95    = result?.percentile_95_arrival_days ?? 0;
  const isRisk = result?.risk_assessment === 'CRITICAL';
  const totalMean = legs.reduce((s, l) => s + l.mean_days, 0);
  const totalStd  = Math.sqrt(legs.reduce((s, l) => s + l.std_days ** 2, 0));

  const { points } = buildDistributionCurve(legs, targetDays);

  const cvarCost = (p95 - targetDays) * legs.reduce((s, l) => s + l.cost_per_day, 0);

  function normCDFInv(p: number) {
    const t = Math.sqrt(-2 * Math.log(p < 0.5 ? p : 1 - p));
    const c = [2.515517, 0.802853, 0.010328];
    const d = [1.432788, 0.189269, 0.001308];
    const raw = t - (c[0] + c[1] * t + c[2] * t ** 2) / (1 + d[0] * t + d[1] * t ** 2 + d[2] * t ** 3);
    return p < 0.5 ? -raw : raw;
  }
  const ladder = [0.50, 0.75, 0.90, 0.95, 0.99].map(q => ({
    label: `P${Math.round(q * 100)}`,
    days:  parseFloat((totalMean + normCDFInv(q) * totalStd).toFixed(1)),
    onTime: (totalMean + normCDFInv(q) * totalStd) <= targetDays,
  }));

  const sens = sensitivityRows(legs, targetDays, prob);

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-3 gap-2">
        <StatBox
          label="On-Time Probability"
          value={`${(prob * 100).toFixed(1)}%`}
          color={isRisk ? 'text-critical' : 'text-safe'}
          sub={`${result?.simulations_run?.toLocaleString()} simulations`}
        />
        <StatBox
          label="P95 Arrival"
          value={`${p95}d`}
          sub={`target: ${targetDays}d`}
          color={p95 > targetDays ? 'text-critical' : 'text-safe'}
        />
        <StatBox
          label="CVaR Tail Cost"
          value={fmt$(cvarCost > 0 ? cvarCost : 0)}
          sub="Expected cost if P95 scenario occurs"
          color="text-warning"
        />
      </div>

      <div>
        <div className="text-[9px] font-bold text-muted uppercase mb-1">
          Arrival Distribution (μ={totalMean.toFixed(1)}d σ={totalStd.toFixed(1)}d)
        </div>
        <p className="text-[9px] text-muted mb-2">
          Green area = on-time probability. Red area = late. Dashed line = target ({targetDays}d).
        </p>
        <ResponsiveContainer width="100%" height={180}>
          <AreaChart data={points} margin={{ top: 4, right: 8, left: -20, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="rgba(255,255,255,0.06)" />
            <XAxis dataKey="days" tick={{ fontSize: 8, fill: '#64748b' }} axisLine={false} tickLine={false} unit="d"
              tickFormatter={v => Number(v).toFixed(0)} />
            <YAxis hide />
            <Tooltip
              contentStyle={{ fontSize: 9, borderRadius: 6 }}
              formatter={(v: any, name: any) => [Number(v).toFixed(4), name === 'onTime' ? 'On-Time' : 'Late']}
              labelFormatter={l => `Arrival: ${l}d`}
            />
            <ReferenceLine x={targetDays} stroke="#94a3b8" strokeDasharray="4 2"
              label={{ value: `Target ${targetDays}d`, position: 'top', fontSize: 8, fill: '#94a3b8' }} />
            <defs>
              <linearGradient id="mcGreen" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%"  stopColor="#22c55e" stopOpacity={0.5} />
                <stop offset="95%" stopColor="#22c55e" stopOpacity={0.05} />
              </linearGradient>
              <linearGradient id="mcRed" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%"  stopColor="#ef4444" stopOpacity={0.5} />
                <stop offset="95%" stopColor="#ef4444" stopOpacity={0.05} />
              </linearGradient>
            </defs>
            <Area type="monotone" dataKey="onTime" stroke="#22c55e" strokeWidth={2} fill="url(#mcGreen)" />
            <Area type="monotone" dataKey="late"   stroke="#ef4444" strokeWidth={2} fill="url(#mcRed)"   />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      <div>
        <div className="text-[9px] font-bold text-muted uppercase mb-2">Arrival Percentile Ladder</div>
        <div className="grid grid-cols-5 gap-1">
          {ladder.map(l => (
            <div
              key={l.label}
              className="p-2 rounded-xl text-center"
              style={{
                background: l.onTime ? 'rgba(34,197,94,0.1)' : 'rgba(239,68,68,0.1)',
                border: `1px solid ${l.onTime ? 'rgba(34,197,94,0.3)' : 'rgba(239,68,68,0.3)'}`,
              }}
            >
              <div className="text-[9px] font-bold text-muted">{l.label}</div>
              <div className={`text-sm font-black ${l.onTime ? 'text-safe' : 'text-critical'}`}>{l.days}d</div>
            </div>
          ))}
        </div>
      </div>

      <div>
        <div className="text-[9px] font-bold text-muted uppercase mb-2">Leg-by-Leg Contribution</div>
        <div className="space-y-1">
          {legs.map((leg, i) => {
            const sharePct = Math.round((leg.mean_days / totalMean) * 100);
            return (
              <div key={i} className="flex items-center gap-3 p-2 bg-surface rounded-xl border border-subtle">
                <div className="text-[10px] font-black text-primary w-24 shrink-0">{leg.label}</div>
                <div className="flex-1">
                  <div className="h-1.5 rounded-full bg-subtle overflow-hidden">
                    <div className="h-full rounded-full bg-brand-primary" style={{ width: `${sharePct}%` }} />
                  </div>
                </div>
                <div className="text-[9px] text-right text-muted font-mono shrink-0">
                  {leg.mean_days} ± {leg.std_days}d ({sharePct}%)
                </div>
              </div>
            );
          })}
        </div>
      </div>

      <div>
        <div className="text-[9px] font-bold text-muted uppercase mb-2">
          Sensitivity — If Each Leg Adds +2 Days
        </div>
        <table className="w-full text-[10px]">
          <thead>
            <tr className="text-[9px] text-muted uppercase border-b border-subtle">
              <th className="text-left pb-2 pr-3">Leg</th>
              <th className="text-right pb-2 pr-3">New P(on-time)</th>
              <th className="text-right pb-2">Delta</th>
            </tr>
          </thead>
          <tbody>
            {sens.map(s => (
              <tr key={s.leg} className="border-b border-subtle/30">
                <td className="py-1.5 pr-3 font-mono text-primary">{s.leg}</td>
                <td className="pr-3 text-right font-black" style={{ color: s.newProb < 0.8 ? '#ef4444' : '#22c55e' }}>
                  {(s.newProb * 100).toFixed(1)}%
                </td>
                <td className={`text-right font-mono ${s.delta < 0 ? 'text-critical' : 'text-safe'}`}>
                  {s.delta < 0 ? '' : '+'}{(s.delta * 100).toFixed(1)}pp
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

const MonteCarloPanel: React.FC = () => {
  const [loading, setLoading]     = useState(false);
  const [response, setResponse]   = useState<JobResponse | null>(null);
  const [error, setError]         = useState('');
  const [simulations, setSimulations] = useState(10000);
  const [targetDays, setTargetDays]   = useState(21);

  const run = async () => {
    setLoading(true); setError(''); setResponse(null);
    try {
      setResponse(await apiService.runMonteCarloRisk(
        MC_LEGS.map(l => ({ mean_days: l.mean_days, std_days: l.std_days, cost_per_day: l.cost_per_day })),
        targetDays, simulations,
      ) as JobResponse);
    } catch (e: any) { setError(e.message); }
    finally { setLoading(false); }
  };

  return (
    <Section title="Monte Carlo Risk Simulation" sub="POST /optimization/monte_carlo_risk — Probabilistic CVaR across N scenarios (NumPy)" badge="Stochastic">
      <div className="grid grid-cols-3 gap-3 mb-4 text-[10px]">
        {MC_LEGS.map((l, i) => (
          <div key={i} className="p-2.5 bg-surface rounded-xl border border-subtle">
            <div className="text-[9px] font-bold text-muted uppercase mb-1">{l.label}</div>
            <div className="flex justify-between"><span className="text-secondary">Transit</span><span className="font-mono">{l.mean_days} ± {l.std_days}d</span></div>
            <div className="flex justify-between"><span className="text-secondary">Cost/day</span><span className="font-mono">${l.cost_per_day.toLocaleString()}</span></div>
          </div>
        ))}
      </div>

      <div className="flex gap-4 mb-4">
        <div>
          <label className="text-[9px] font-bold text-muted uppercase block mb-1">Target Days</label>
          <input type="number" className="bg-surface border border-subtle rounded-lg px-3 py-2 text-xs text-primary w-24"
            value={targetDays} onChange={e => setTargetDays(parseInt(e.target.value))} />
        </div>
        <div>
          <label className="text-[9px] font-bold text-muted uppercase block mb-1">Simulations</label>
          <select className="bg-surface border border-subtle rounded-lg px-3 py-2 text-xs text-primary"
            value={simulations} onChange={e => setSimulations(parseInt(e.target.value))}>
            <option value={1000}>1,000</option>
            <option value={10000}>10,000</option>
            <option value={50000}>50,000</option>
          </select>
        </div>
      </div>

      <button className="btn-primary text-xs flex items-center gap-2" onClick={run} disabled={loading}>
        {loading ? <Loader2 size={12} className="animate-spin" /> : <Zap size={12} />}
        Run {simulations.toLocaleString()} Scenarios
      </button>

      {response && (
        <JobPoller
          response={response}
          resultRenderer={r => <MonteCarloResult result={r} legs={MC_LEGS} targetDays={targetDays} />}
        />
      )}
      {error && <Err msg={error} />}
    </Section>
  );
};

// ── 5. INVENTORY MEIO ─────────────────────────────────────────────────────────

const MEIO_NODES = [
  { node_id: 'DC-EAST',  demand_mean: 450, demand_std: 80,  lead_time_days: 7,  holding_cost: 12 },
  { node_id: 'DC-WEST',  demand_mean: 320, demand_std: 60,  lead_time_days: 10, holding_cost: 11 },
  { node_id: 'HUB-MAIN', demand_mean: 900, demand_std: 140, lead_time_days: 3,  holding_cost: 8  },
];

const MEIOResult: React.FC<{ result: any; serviceLevel: number }> = ({ result, serviceLevel }) => {
  const nodes: any[] = Array.isArray(result) ? result : [];

  const chartData = nodes.map((n: any) => {
    const src = MEIO_NODES.find(m => m.node_id === n.node_id);
    const naive = src ? src.demand_mean * src.lead_time_days : 0;
    const annualSavings = src
      ? (naive - n.optimal_total_inventory) * src.holding_cost * 12
      : 0;
    return {
      node:         n.node_id,
      naïve:        naive,
      optimal:      n.optimal_total_inventory,
      safetyStock:  n.optimal_safety_stock,
      annualSavings: Math.max(0, annualSavings),
    };
  });

  const totalAnnualSavings = chartData.reduce((s, r) => s + r.annualSavings, 0);

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-3 gap-2">
        <StatBox label="Service Level" value={`${(serviceLevel * 100).toFixed(1)}%`} sub={`z = ${nodes[0]?.z_score_used ?? '—'}`} />
        <StatBox label="Nodes Optimised" value={nodes.length} />
        <StatBox label="Est. Annual Holding Savings" value={fmt$(totalAnnualSavings)} color="text-safe" sub="vs naïve demand×lead-time" />
      </div>

      {chartData.length > 0 && (
        <>
          <div className="text-[9px] font-bold text-muted uppercase mb-1">Inventory: Naïve vs Optimal vs Safety Stock</div>
          <p className="text-[9px] text-muted mb-2">
            Naïve = demand × lead time (no variability buffer). Optimal adds statistically derived safety stock.
          </p>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={chartData} margin={{ top: 4, right: 8, left: -10, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="rgba(255,255,255,0.06)" />
              <XAxis dataKey="node" tick={{ fontSize: 9, fill: '#64748b' }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fontSize: 9, fill: '#64748b' }} axisLine={false} tickLine={false} />
              <Tooltip contentStyle={{ fontSize: 10, borderRadius: 6 }} />
              <Legend iconSize={8} wrapperStyle={{ fontSize: 9 }} />
              <Bar dataKey="naïve"       fill="#64748b" radius={[3, 3, 0, 0]} name="Naïve" />
              <Bar dataKey="optimal"     fill="#3b82f6" radius={[3, 3, 0, 0]} name="Optimal Total" />
              <Bar dataKey="safetyStock" fill="#22c55e" radius={[3, 3, 0, 0]} name="Safety Stock" />
            </BarChart>
          </ResponsiveContainer>
        </>
      )}

      <div className="space-y-2">
        {chartData.map(r => (
          <div key={r.node} className="flex items-center justify-between p-3 bg-surface rounded-xl border border-subtle">
            <span className="text-[10px] font-mono font-black text-primary">{r.node}</span>
            <div className="flex gap-4 text-[10px]">
              <div><span className="text-muted">Safety stock </span><span className="font-black text-primary">{r.safetyStock.toLocaleString()}</span></div>
              <div><span className="text-muted">Optimal total </span><span className="font-black text-safe">{r.optimal.toLocaleString()}</span></div>
              <div><span className="text-muted">Annual saving </span><span className="font-black text-brand-primary">{fmt$(r.annualSavings)}</span></div>
            </div>
          </div>
        ))}
      </div>

      <div className="p-3 rounded-xl bg-brand-primary/5 border border-brand-primary/20 text-[10px] text-secondary">
        <strong className="text-primary">Reorder cadence:</strong> with a weekly order cycle (7-day EOQ),
        each node replenishes every 7 days. Safety stock buffers demand variability
        so the <strong>{(serviceLevel * 100).toFixed(0)}%</strong> fill rate is maintained even during
        lead-time spikes — holding cost per unit is factored into the optimal total above.
      </div>
    </div>
  );
};

const InventoryQueuePanel: React.FC = () => {
  const [loading, setLoading]   = useState(false);
  const [response, setResponse] = useState<JobResponse | null>(null);
  const [error, setError]       = useState('');
  const [serviceLevel, setServiceLevel] = useState(0.95);

  const run = async () => {
    setLoading(true); setError(''); setResponse(null);
    try { setResponse(await apiService.optimizeInventoryQueue(MEIO_NODES, serviceLevel) as JobResponse); }
    catch (e: any) { setError(e.message); }
    finally { setLoading(false); }
  };

  return (
    <Section title="Inventory MEIO Optimizer" sub="POST /optimization/inventory_meio — Safety stock across distribution network (scipy z-score)" badge="MEIO">
      <div className="mb-3 text-[10px] space-y-1">
        {MEIO_NODES.map(n => (
          <div key={n.node_id} className="flex items-center justify-between p-2 bg-surface rounded-lg border border-subtle">
            <span className="font-mono font-black text-primary">{n.node_id}</span>
            <span className="text-secondary">μ={n.demand_mean} σ={n.demand_std}</span>
            <span className="text-muted">LT: {n.lead_time_days}d · HC: ${n.holding_cost}/unit/mo</span>
          </div>
        ))}
      </div>
      <div className="flex items-center gap-4 mb-3">
        <div>
          <label className="text-[9px] font-bold text-muted uppercase block mb-1">Service Level</label>
          <input
            type="number" step="0.01" min="0.8" max="0.999"
            className="bg-surface border border-subtle rounded-lg px-3 py-2 text-xs text-primary w-24"
            value={serviceLevel} onChange={e => setServiceLevel(parseFloat(e.target.value))}
          />
        </div>
        <div className="text-[10px] text-secondary mt-4">
          Fill rate target: <strong>{(serviceLevel * 100).toFixed(1)}%</strong>
          <div className="text-[9px] text-muted">Higher SL → larger safety stock → higher holding cost</div>
        </div>
      </div>
      <button className="btn-primary text-xs flex items-center gap-2" onClick={run} disabled={loading}>
        {loading ? <Loader2 size={12} className="animate-spin" /> : <Zap size={12} />}
        Optimize Inventory
      </button>
      {response && (
        <JobPoller
          response={response}
          resultRenderer={r => <MEIOResult result={r} serviceLevel={serviceLevel} />}
        />
      )}
      {error && <Err msg={error} />}
    </Section>
  );
};

// ── Overview ──────────────────────────────────────────────────────────────────

type OptSubView = 'overview' | 'delay' | 'efi' | 'network' | 'montecarlo' | 'inventory';

const RADAR_DATA = [
  { metric: 'Delay Safety',        portfolio: 72, industry: 78 },
  { metric: 'EFI Performance',     portfolio: 84, industry: 75 },
  { metric: 'Network Efficiency',  portfolio: 91, industry: 82 },
  { metric: 'Schedule Confidence', portfolio: 68, industry: 74 },
  { metric: 'Inventory Health',    portfolio: 79, industry: 80 },
];

const TIMELINE_DATA = [
  { week: 'W1',  efficiency: 74, riskScore: 48, costIndex: 92 },
  { week: 'W2',  efficiency: 76, riskScore: 45, costIndex: 90 },
  { week: 'W3',  efficiency: 75, riskScore: 50, costIndex: 91 },
  { week: 'W4',  efficiency: 78, riskScore: 43, costIndex: 88 },
  { week: 'W5',  efficiency: 80, riskScore: 41, costIndex: 87 },
  { week: 'W6',  efficiency: 79, riskScore: 44, costIndex: 86 },
  { week: 'W7',  efficiency: 82, riskScore: 39, costIndex: 84 },
  { week: 'W8',  efficiency: 84, riskScore: 37, costIndex: 83 },
  { week: 'W9',  efficiency: 83, riskScore: 40, costIndex: 83 },
  { week: 'W10', efficiency: 86, riskScore: 35, costIndex: 81 },
  { week: 'W11', efficiency: 88, riskScore: 33, costIndex: 80 },
  { week: 'W12', efficiency: 91, riskScore: 30, costIndex: 78 },
];

const ENGINE_CARDS: {
  key: OptSubView;
  label: string;
  badge: string;
  desc: string;
  metric: string;
  metricLabel: string;
  color: string;
  icon: React.ElementType;
}[] = [
  {
    key: 'delay', label: 'Delay Prediction', badge: 'ML',
    desc: 'XGBoost regressor across shipment portfolio predicts per-shipment delay risk.',
    metric: '+1.4d', metricLabel: 'Avg predicted delay',
    color: '#f97316', icon: Zap,
  },
  {
    key: 'efi', label: 'EFI Portfolio', badge: 'MIP',
    desc: 'Stochastic MIP selects optimal action set under budget and CVaR constraints.',
    metric: '$18.2k', metricLabel: 'Best EFI action',
    color: '#3b82f6', icon: BarChart3,
  },
  {
    key: 'network', label: 'Network Router', badge: 'MILP',
    desc: 'Min-cost flow with capacity constraints routes FEU across global lanes.',
    metric: '$3.6M', metricLabel: 'Optimal lane cost',
    color: '#8b5cf6', icon: Network,
  },
  {
    key: 'montecarlo', label: 'Monte Carlo', badge: 'Stochastic',
    desc: 'Probabilistic CVaR across 10k+ scenarios with arrival distribution curves.',
    metric: '87.3%', metricLabel: 'P(on-time)',
    color: '#22c55e', icon: TrendingUp,
  },
  {
    key: 'inventory', label: 'Inventory MEIO', badge: 'MEIO',
    desc: 'Safety stock optimisation across multi-echelon distribution network.',
    metric: '$142k', metricLabel: 'Est. annual savings',
    color: '#ec4899', icon: Package,
  },
];

const OptimizationOverview: React.FC<{ onNavigate: (sv: OptSubView) => void }> = ({ onNavigate }) => (
  <div>
    {/* Header */}
    <div className="mb-6">
      <div className="flex items-center gap-3 mb-1">
        <Layers size={22} style={{ color: 'var(--brand-primary)' }} />
        <h2 style={{ fontSize: '1.5rem', fontWeight: 900, letterSpacing: '-0.02em', color: 'var(--text-primary)' }}>
          Optimization Engine
        </h2>
      </div>
      <p style={{ fontSize: 13, color: 'var(--text-secondary)' }}>
        Portfolio health radar and 12-week performance timeline across all five solvers.
        Click any engine card to dive into its full analytical panel.
      </p>
    </div>

    {/* Charts row */}
    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1.4fr', gap: 20, marginBottom: 24 }}>
      {/* Radar */}
      <div className="glass-panel" style={{ padding: '20px 16px' }}>
        <div style={{ fontSize: 10, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--text-tertiary)', marginBottom: 12 }}>
          Portfolio Health Radar
        </div>
        <ResponsiveContainer width="100%" height={240}>
          <RadarChart data={RADAR_DATA} margin={{ top: 10, right: 30, bottom: 10, left: 30 }}>
            <PolarGrid stroke="rgba(148,163,184,0.2)" />
            <PolarAngleAxis dataKey="metric" tick={{ fontSize: 9, fill: 'var(--text-tertiary)' }} />
            <PolarRadiusAxis domain={[0, 100]} tick={false} axisLine={false} />
            <Radar name="Industry Avg" dataKey="industry" stroke="#94a3b8" fill="#94a3b8" fillOpacity={0.15} strokeWidth={1.5} strokeDasharray="4 2" />
            <Radar name="Your Portfolio" dataKey="portfolio" stroke="var(--brand-primary)" fill="var(--brand-primary)" fillOpacity={0.25} strokeWidth={2} />
            <Legend iconSize={8} wrapperStyle={{ fontSize: 9 }} />
            <Tooltip contentStyle={{ fontSize: 10, borderRadius: 6 }} />
          </RadarChart>
        </ResponsiveContainer>
      </div>

      {/* Timeline */}
      <div className="glass-panel" style={{ padding: '20px 16px' }}>
        <div style={{ fontSize: 10, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--text-tertiary)', marginBottom: 12 }}>
          12-Week Portfolio Trend
        </div>
        <ResponsiveContainer width="100%" height={240}>
          <AreaChart data={TIMELINE_DATA} margin={{ top: 4, right: 8, left: -24, bottom: 0 }}>
            <defs>
              <linearGradient id="gEff" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.35} />
                <stop offset="95%" stopColor="#3b82f6" stopOpacity={0.03} />
              </linearGradient>
              <linearGradient id="gRisk" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#ef4444" stopOpacity={0.35} />
                <stop offset="95%" stopColor="#ef4444" stopOpacity={0.03} />
              </linearGradient>
              <linearGradient id="gCost" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#22c55e" stopOpacity={0.25} />
                <stop offset="95%" stopColor="#22c55e" stopOpacity={0.03} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="rgba(148,163,184,0.12)" />
            <XAxis dataKey="week" tick={{ fontSize: 9, fill: '#64748b' }} axisLine={false} tickLine={false} />
            <YAxis domain={[20, 100]} tick={{ fontSize: 9, fill: '#64748b' }} axisLine={false} tickLine={false} />
            <Tooltip contentStyle={{ fontSize: 10, borderRadius: 6 }} />
            <Legend iconSize={8} wrapperStyle={{ fontSize: 9 }} />
            <Area type="monotone" dataKey="efficiency" name="Efficiency" stroke="#3b82f6" strokeWidth={2} fill="url(#gEff)" dot={false} />
            <Area type="monotone" dataKey="riskScore"  name="Risk Score" stroke="#ef4444" strokeWidth={2} fill="url(#gRisk)" dot={false} />
            <Area type="monotone" dataKey="costIndex"  name="Cost Index" stroke="#22c55e" strokeWidth={2} fill="url(#gCost)" dot={false} />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>

    {/* Engine cards */}
    <div style={{ fontSize: 10, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--text-tertiary)', marginBottom: 12 }}>
      Optimization Engines — Click to Open
    </div>
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 12 }}>
      {ENGINE_CARDS.map(card => {
        const Icon = card.icon;
        return (
          <button
            key={card.key}
            onClick={() => onNavigate(card.key)}
            style={{
              background: 'var(--bg-surface)',
              border: '1px solid var(--border-subtle)',
              borderRadius: 12,
              padding: '16px 14px',
              textAlign: 'left',
              cursor: 'pointer',
              transition: 'border-color 0.15s, box-shadow 0.15s',
            }}
            onMouseEnter={e => {
              (e.currentTarget as HTMLElement).style.borderColor = card.color;
              (e.currentTarget as HTMLElement).style.boxShadow = `0 0 0 2px ${card.color}22`;
            }}
            onMouseLeave={e => {
              (e.currentTarget as HTMLElement).style.borderColor = 'var(--border-subtle)';
              (e.currentTarget as HTMLElement).style.boxShadow = 'none';
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10 }}>
              <Icon size={16} style={{ color: card.color }} />
              <span style={{
                fontSize: 8, fontWeight: 800, padding: '2px 6px', borderRadius: 4,
                background: card.color + '20', color: card.color, textTransform: 'uppercase', letterSpacing: '0.04em',
              }}>
                {card.badge}
              </span>
            </div>
            <div style={{ fontSize: 12, fontWeight: 800, color: 'var(--text-primary)', marginBottom: 4 }}>{card.label}</div>
            <div style={{ fontSize: 10, color: 'var(--text-tertiary)', lineHeight: 1.4, marginBottom: 12 }}>{card.desc}</div>
            <div style={{ borderTop: '1px solid var(--border-subtle)', paddingTop: 10 }}>
              <div style={{ fontSize: 17, fontWeight: 900, color: card.color }}>{card.metric}</div>
              <div style={{ fontSize: 9, color: 'var(--text-tertiary)' }}>{card.metricLabel}</div>
            </div>
          </button>
        );
      })}
    </div>
  </div>
);

// ── Main page ─────────────────────────────────────────────────────────────────

interface OptimizationPageProps {
  subView?: OptSubView;
  onSubNavigate?: (sv: OptSubView) => void;
}

const SUB_TITLES: Record<OptSubView, string> = {
  overview:   'Optimizer Overview',
  delay:      'Delay Prediction',
  efi:        'EFI Portfolio Optimizer',
  network:    'Network Router',
  montecarlo: 'Monte Carlo Simulation',
  inventory:  'Inventory MEIO',
};

export const OptimizationPage: React.FC<OptimizationPageProps> = ({ subView = 'overview', onSubNavigate }) => {
  const goBack = () => onSubNavigate?.('overview');

  return (
    <div style={{ padding: '32px 40px', maxWidth: 1100, margin: '0 auto' }}>
      {/* Breadcrumb for sub-views */}
      {subView !== 'overview' && (
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 20 }}>
          <button
            onClick={goBack}
            style={{
              display: 'flex', alignItems: 'center', gap: 6,
              fontSize: 11, fontWeight: 700, color: 'var(--brand-primary)',
              background: 'none', border: 'none', cursor: 'pointer', padding: 0,
            }}
          >
            <ArrowLeft size={13} /> Optimizer Overview
          </button>
          <span style={{ fontSize: 11, color: 'var(--text-tertiary)' }}>/</span>
          <span style={{ fontSize: 11, fontWeight: 700, color: 'var(--text-primary)' }}>
            {SUB_TITLES[subView]}
          </span>
        </div>
      )}

      {subView === 'overview' && onSubNavigate && (
        <OptimizationOverview onNavigate={onSubNavigate} />
      )}

      {subView === 'delay'      && <DelayPredictionPanel />}
      {subView === 'efi'        && <EFIOptimizerPanel />}
      {subView === 'network'    && <NetworkOptimizerPanel />}
      {subView === 'montecarlo' && <MonteCarloPanel />}
      {subView === 'inventory'  && <InventoryQueuePanel />}
    </div>
  );
};
