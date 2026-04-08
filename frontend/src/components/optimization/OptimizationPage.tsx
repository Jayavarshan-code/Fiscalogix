import React, { useState } from 'react';
import { Loader2, Zap, CheckCircle, AlertTriangle, ChevronDown, ChevronUp, Clock } from 'lucide-react';
import { apiService } from '../../services/api';

// ── helpers ───────────────────────────────────────────────────────────────────
const Section: React.FC<{ title: string; sub: string; badge?: string; children: React.ReactNode }> = ({
  title, sub, badge, children
}) => {
  const [open, setOpen] = useState(true);
  return (
    <div className="glass-panel p-5 mb-6 rounded-2xl border border-subtle">
      <button className="flex justify-between items-center w-full mb-4" onClick={() => setOpen(!open)}>
        <div className="text-left flex items-center gap-3">
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-sm font-black text-primary uppercase tracking-tight">{title}</h3>
              {badge && <span className="text-[8px] font-black px-2 py-0.5 bg-brand-primary/10 text-brand-primary rounded-full border border-brand-primary/30 uppercase">{badge}</span>}
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

const JobAccepted: React.FC<{ jobId: string }> = ({ jobId }) => (
  <div className="mt-3 p-3 bg-safe/10 border border-safe/30 rounded-xl flex items-center gap-3">
    <CheckCircle size={16} className="text-safe shrink-0" />
    <div>
      <div className="text-[10px] font-black text-safe uppercase">Job Accepted — Running in Background</div>
      <div className="text-[10px] text-secondary mt-0.5 font-mono">Job ID: {jobId}</div>
      <div className="text-[10px] text-muted mt-0.5 flex items-center gap-1">
        <Clock size={10} /> Results available via job queue polling (production: webhook / SSE)
      </div>
    </div>
  </div>
);

const Err: React.FC<{ msg: string }> = ({ msg }) => (
  <div className="mt-3 flex items-center gap-2 text-critical text-[11px] p-3 bg-critical/10 rounded-xl border border-critical/30">
    <AlertTriangle size={14} /> {msg}
  </div>
);

// ── Delay Prediction ──────────────────────────────────────────────────────────
const DelayPredictionPanel: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState('');
  const [rows, setRows] = useState([
    { shipment_id: 'SYS-1001', route: 'CN-US', order_value: 500000, credit_days: 30, carrier: 'COSCO' },
    { shipment_id: 'SYS-1002', route: 'EU-US', order_value: 210000, credit_days: 45, carrier: 'Maersk' },
    { shipment_id: 'SYS-1003', route: 'IN-AE', order_value: 85000,  credit_days: 30, carrier: 'MSC' },
  ]);

  const run = async () => {
    setLoading(true); setError(''); setResult(null);
    try { setResult(await apiService.predictDelay(rows)); }
    catch (e: any) { setError(e.message); }
    finally { setLoading(false); }
  };

  const delayColor = (d: number) => d > 4 ? 'text-critical' : d > 2 ? 'text-warning' : 'text-safe';

  return (
    <Section title="Batch Delay Prediction" sub="POST /api/v1/predict/delay — Stochastic delay model v2.1 across shipment portfolio" badge="ML v2.1">
      <div className="overflow-x-auto mb-3">
        <table className="w-full text-[10px]">
          <thead>
            <tr className="text-muted text-[9px] uppercase border-b border-subtle">
              <th className="text-left pb-2 pr-3">Shipment ID</th>
              <th className="text-left pb-2 pr-3">Route</th>
              <th className="text-right pb-2 pr-3">Value</th>
              <th className="text-right pb-2">Credit Days</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r, i) => (
              <tr key={i} className="border-b border-subtle/30">
                <td className="py-1.5 pr-3 font-mono text-primary">{r.shipment_id}</td>
                <td className="pr-3 text-secondary">{r.route}</td>
                <td className="pr-3 text-right">${r.order_value.toLocaleString()}</td>
                <td className="text-right text-secondary">{r.credit_days}d</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <button className="btn-primary text-xs flex items-center gap-2" onClick={run} disabled={loading}>
        {loading ? <Loader2 size={12} className="animate-spin" /> : <Zap size={12} />}
        Predict Delay for {rows.length} Shipments
      </button>
      {result && (
        <div className="mt-3">
          <div className="text-[9px] font-bold text-muted uppercase mb-2">
            Predictions · Model: {result.model_version}
          </div>
          <div className="space-y-1">
            {result.predictions?.map((p: any) => (
              <div key={p.shipment_id} className="flex items-center justify-between p-2.5 bg-surface rounded-xl border border-subtle">
                <span className="text-[10px] font-mono text-primary">{p.shipment_id}</span>
                <div className="flex items-center gap-3">
                  <span className={`text-sm font-black ${delayColor(p.predicted_delay_days)}`}>
                    +{p.predicted_delay_days.toFixed(1)} days
                  </span>
                  <span className="text-[9px] text-muted">
                    {p.predicted_delay_days > 4 ? 'CRITICAL' : p.predicted_delay_days > 2 ? 'DELAYED' : 'ON TRACK'}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
      {error && <Err msg={error} />}
    </Section>
  );
};

// ── Network Routing Optimizer ─────────────────────────────────────────────────
const NetworkOptimizerPanel: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [jobResult, setJobResult] = useState<any>(null);
  const [error, setError] = useState('');

  // Demo payload — 2-origin 2-destination problem
  const demoPayload = {
    origins: ['Shanghai', 'Rotterdam'],
    destinations: ['Los Angeles', 'New York'],
    supply: { 'Shanghai': 1200, 'Rotterdam': 800 },
    demand: { 'Los Angeles': 900, 'New York': 1100 },
    costs: {
      'Shanghai':   { 'Los Angeles': 1850, 'New York': 2100 },
      'Rotterdam':  { 'Los Angeles': 2300, 'New York': 1650 },
    },
    capacities: {
      'Shanghai':   { 'Los Angeles': 1000, 'New York': 800 },
      'Rotterdam':  { 'Los Angeles': 700,  'New York': 900 },
    },
  };

  const run = async () => {
    setLoading(true); setError(''); setJobResult(null);
    try { setJobResult(await apiService.optimizeNetwork(demoPayload)); }
    catch (e: any) { setError(e.message); }
    finally { setLoading(false); }
  };

  return (
    <Section title="MILP Network Routing Optimizer" sub="POST /optimization/network — Minimum cost flow with capacity constraints" badge="MILP">
      <div className="mb-3 text-[10px] text-secondary">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <div className="text-[9px] font-bold text-muted uppercase mb-1">Origins → Supply</div>
            {Object.entries(demoPayload.supply).map(([k, v]) => (
              <div key={k} className="flex justify-between py-0.5"><span>{k}</span><span className="font-mono">{v} FEU</span></div>
            ))}
          </div>
          <div>
            <div className="text-[9px] font-bold text-muted uppercase mb-1">Destinations → Demand</div>
            {Object.entries(demoPayload.demand).map(([k, v]) => (
              <div key={k} className="flex justify-between py-0.5"><span>{k}</span><span className="font-mono">{v} FEU</span></div>
            ))}
          </div>
        </div>
      </div>
      <button className="btn-primary text-xs flex items-center gap-2" onClick={run} disabled={loading}>
        {loading ? <Loader2 size={12} className="animate-spin" /> : <Zap size={12} />}
        Dispatch to MILP Solver
      </button>
      {jobResult && <JobAccepted jobId={jobResult.job_id} />}
      {error && <Err msg={error} />}
    </Section>
  );
};

// ── Monte Carlo Risk ──────────────────────────────────────────────────────────
const MonteCarloPanel: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [jobResult, setJobResult] = useState<any>(null);
  const [error, setError] = useState('');
  const [simulations, setSimulations] = useState(10000);
  const [targetDays, setTargetDays] = useState(21);

  const legs = [
    { mean_days: 14.0, std_days: 2.5, cost_per_day: 3200 },
    { mean_days: 3.0,  std_days: 1.0, cost_per_day: 850  },
    { mean_days: 2.0,  std_days: 0.5, cost_per_day: 420  },
  ];

  const run = async () => {
    setLoading(true); setError(''); setJobResult(null);
    try { setJobResult(await apiService.runMonteCarloRisk(legs, targetDays, simulations)); }
    catch (e: any) { setError(e.message); }
    finally { setLoading(false); }
  };

  return (
    <Section title="Monte Carlo Risk Simulation" sub="POST /optimization/monte_carlo_risk — Step-cost CVaR across 10,000 scenarios" badge="Stochastic">
      <div className="grid grid-cols-3 gap-3 mb-3 text-[10px]">
        {legs.map((l, i) => (
          <div key={i} className="p-2.5 bg-surface rounded-xl border border-subtle">
            <div className="text-[9px] font-bold text-muted uppercase mb-1">Leg {i + 1}</div>
            <div className="flex justify-between"><span className="text-secondary">Transit</span><span className="font-mono">{l.mean_days} ± {l.std_days}d</span></div>
            <div className="flex justify-between"><span className="text-secondary">Cost/day</span><span className="font-mono">${l.cost_per_day}</span></div>
          </div>
        ))}
      </div>
      <div className="flex gap-4 mb-3">
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
      {jobResult && <JobAccepted jobId={jobResult.job_id} />}
      {error && <Err msg={error} />}
    </Section>
  );
};

// ── Inventory MEIO Queue ──────────────────────────────────────────────────────
const InventoryQueuePanel: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [jobResult, setJobResult] = useState<any>(null);
  const [error, setError] = useState('');
  const [serviceLevel, setServiceLevel] = useState(0.95);

  const nodes = [
    { node_id: 'DC-EAST',  demand_mean: 450, demand_std: 80,  lead_time_days: 7,  holding_cost: 12 },
    { node_id: 'DC-WEST',  demand_mean: 320, demand_std: 60,  lead_time_days: 10, holding_cost: 11 },
    { node_id: 'HUB-MAIN', demand_mean: 900, demand_std: 140, lead_time_days: 3,  holding_cost: 8  },
  ];

  const run = async () => {
    setLoading(true); setError(''); setJobResult(null);
    try { setJobResult(await apiService.optimizeInventoryQueue(nodes, serviceLevel)); }
    catch (e: any) { setError(e.message); }
    finally { setLoading(false); }
  };

  return (
    <Section title="Inventory MEIO — Job Queue" sub="POST /optimization/inventory_meio — Safety stock across distribution network" badge="Queue">
      <div className="mb-3 text-[10px] space-y-1">
        {nodes.map(n => (
          <div key={n.node_id} className="flex items-center justify-between p-2 bg-surface rounded-lg border border-subtle">
            <span className="font-mono font-bold text-primary">{n.node_id}</span>
            <span className="text-secondary">μ={n.demand_mean} σ={n.demand_std}</span>
            <span className="text-muted">LT: {n.lead_time_days}d · HC: ${n.holding_cost}</span>
          </div>
        ))}
      </div>
      <div className="flex items-center gap-4 mb-3">
        <div>
          <label className="text-[9px] font-bold text-muted uppercase block mb-1">Service Level</label>
          <input type="number" step="0.01" min="0.8" max="0.999"
            className="bg-surface border border-subtle rounded-lg px-3 py-2 text-xs text-primary w-24"
            value={serviceLevel} onChange={e => setServiceLevel(parseFloat(e.target.value))} />
        </div>
        <div className="text-[10px] text-secondary mt-4">
          Fill rate target: <strong>{(serviceLevel * 100).toFixed(1)}%</strong>
        </div>
      </div>
      <button className="btn-primary text-xs flex items-center gap-2" onClick={run} disabled={loading}>
        {loading ? <Loader2 size={12} className="animate-spin" /> : <Zap size={12} />}
        Queue MEIO Optimization
      </button>
      {jobResult && <JobAccepted jobId={jobResult.job_id} />}
      {error && <Err msg={error} />}
    </Section>
  );
};

// ── EFI Optimizer ─────────────────────────────────────────────────────────────
const EFIOptimizerPanel: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState('');
  const [riskAppetite, setRiskAppetite] = useState('BALANCED');
  const [availableCash, setAvailableCash] = useState(1000000);

  // Demo: 2 shipments × 3 action alternatives each
  const candidateMatrix = [
    [
      { shipment_id: 'SYS-1001', action: 'HOLD',        efi: 12400, cost: 0      },
      { shipment_id: 'SYS-1001', action: 'REROUTE_AIR', efi: 18200, cost: 14000  },
      { shipment_id: 'SYS-1001', action: 'REROUTE_RAIL',efi: 15100, cost: 5200   },
    ],
    [
      { shipment_id: 'SYS-1002', action: 'HOLD',        efi: 8200,  cost: 0      },
      { shipment_id: 'SYS-1002', action: 'EXPEDITE',    efi: 11600, cost: 8800   },
      { shipment_id: 'SYS-1002', action: 'REROUTE_RAIL',efi: 9800,  cost: 3100   },
    ],
  ];

  const run = async () => {
    setLoading(true); setError(''); setResult(null);
    try { setResult(await apiService.optimizeEFI(candidateMatrix, availableCash, riskAppetite)); }
    catch (e: any) { setError(e.message); }
    finally { setLoading(false); }
  };

  return (
    <Section title="EFI Portfolio Optimizer (StochasticMIP)" sub="POST /api/v1/predict/efi — Optimal action set across shipment portfolio under budget constraint" badge="MIP">
      <div className="flex gap-4 mb-3">
        <div>
          <label className="text-[9px] font-bold text-muted uppercase block mb-1">Risk Appetite</label>
          <select className="bg-surface border border-subtle rounded-lg px-3 py-2 text-xs text-primary"
            value={riskAppetite} onChange={e => setRiskAppetite(e.target.value)}>
            <option>CONSERVATIVE</option>
            <option>BALANCED</option>
            <option>AGGRESSIVE</option>
          </select>
        </div>
        <div>
          <label className="text-[9px] font-bold text-muted uppercase block mb-1">Cash Budget ($)</label>
          <input type="number" step="100000" className="bg-surface border border-subtle rounded-lg px-3 py-2 text-xs text-primary w-32"
            value={availableCash} onChange={e => setAvailableCash(parseInt(e.target.value))} />
        </div>
      </div>
      <div className="mb-3 text-[10px] text-secondary">
        {candidateMatrix.map((actions, i) => (
          <div key={i} className="mb-1 flex gap-2 flex-wrap">
            <span className="font-bold text-primary">{actions[0].shipment_id}:</span>
            {actions.map(a => (
              <span key={a.action} className="px-2 py-0.5 bg-surface border border-subtle rounded font-mono">
                {a.action} (EFI ${a.efi.toLocaleString()}, Cost ${a.cost.toLocaleString()})
              </span>
            ))}
          </div>
        ))}
      </div>
      <button className="btn-primary text-xs flex items-center gap-2" onClick={run} disabled={loading}>
        {loading ? <Loader2 size={12} className="animate-spin" /> : <Zap size={12} />}
        Optimize Portfolio ({riskAppetite})
      </button>
      {result && (
        <div className="mt-3">
          <div className="text-[9px] font-bold text-muted uppercase mb-2">
            Optimized Decisions · Algorithm: {result.metadata?.algorithm}
          </div>
          <pre className="p-3 bg-surface rounded-xl border border-subtle text-[10px] text-secondary overflow-auto max-h-48">
            {JSON.stringify(result.optimized_decisions, null, 2)}
          </pre>
        </div>
      )}
      {error && <Err msg={error} />}
    </Section>
  );
};

// ── Main page ─────────────────────────────────────────────────────────────────
export const OptimizationPage: React.FC = () => (
  <div className="p-8 max-w-5xl mx-auto">
    <div className="mb-6">
      <h2 className="text-2xl font-black text-primary tracking-tighter">Optimization Engine (POE)</h2>
      <p className="text-sm text-secondary mt-1">
        Mathematical solvers, stochastic simulation, and ML prediction pipelines.
        Heavy jobs dispatch to the background process pool and return a Job ID.
      </p>
    </div>
    <DelayPredictionPanel />
    <EFIOptimizerPanel />
    <NetworkOptimizerPanel />
    <MonteCarloPanel />
    <InventoryQueuePanel />
  </div>
);
