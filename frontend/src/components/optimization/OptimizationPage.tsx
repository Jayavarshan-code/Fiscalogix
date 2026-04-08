import React, { useState, useEffect, useRef } from 'react';
import { Loader2, Zap, CheckCircle, AlertTriangle, ChevronDown, ChevronUp, Clock, Terminal } from 'lucide-react';
import { apiService } from '../../services/api';

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

const Err: React.FC<{ msg: string }> = ({ msg }) => (
  <div className="mt-3 flex items-center gap-2 text-critical text-[11px] p-3 bg-critical/10 rounded-xl border border-critical/30">
    <AlertTriangle size={14} /> {msg}
  </div>
);

// ── JobPoller ─────────────────────────────────────────────────────────────────
// Renders inline results immediately when Celery is unavailable (status=completed
// returned directly). Polls every 2s when a real job_id is returned.

type JobResponse =
  | { status: 'accepted'; job_id: string }
  | { status: 'completed'; job_id: null; result: any };

type PollState = 'polling' | 'completed' | 'failed' | 'timeout';

const JobPoller: React.FC<{
  response: JobResponse;
  resultRenderer: (result: any) => React.ReactNode;
}> = ({ response, resultRenderer }) => {
  const [pollState, setPollState] = useState<PollState>(
    response.status === 'completed' ? 'completed' : 'polling'
  );
  const [result, setResult]   = useState<any>(response.status === 'completed' ? response.result : null);
  const [error, setError]     = useState('');
  const [elapsed, setElapsed] = useState(0);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    // Inline result — nothing to poll
    if (response.status === 'completed') return;

    const start = Date.now();
    intervalRef.current = setInterval(async () => {
      const secs = Math.floor((Date.now() - start) / 1000);
      setElapsed(secs);

      if (secs > 90) {
        clearInterval(intervalRef.current!);
        setPollState('timeout');
        return;
      }
      try {
        const data = await apiService.getJobStatus(response.job_id);
        if (data.status === 'COMPLETED') {
          clearInterval(intervalRef.current!);
          setResult(data.result);
          setPollState('completed');
        } else if (data.status === 'FAILED') {
          clearInterval(intervalRef.current!);
          setError(data.error || 'Job failed on worker');
          setPollState('failed');
        }
        // PROCESSING — keep polling
      } catch (e: any) {
        clearInterval(intervalRef.current!);
        setError(e.message);
        setPollState('failed');
      }
    }, 2000);

    return () => clearInterval(intervalRef.current!);
  }, [response]);

  if (pollState === 'polling') return (
    <div className="mt-3 p-3 bg-surface border border-subtle rounded-xl flex items-center gap-3">
      <Loader2 size={14} className="animate-spin text-brand-primary shrink-0" />
      <div>
        <div className="text-[10px] font-black text-primary">Running in background…</div>
        <div className="text-[9px] text-muted font-mono mt-0.5">
          {response.job_id} · {elapsed}s elapsed
        </div>
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
        Start Celery worker: <code className="font-mono ml-1">celery -A app.celery_app worker --loglevel=info</code>
      </div>
    </div>
  );

  if (pollState === 'failed') return <Err msg={error} />;

  // completed
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

// ── Result renderers (one per solver) ────────────────────────────────────────

const NetworkResult: React.FC<{ result: any }> = ({ result }) => (
  <div className="space-y-2">
    <div className="grid grid-cols-2 gap-2">
      <div className="p-3 bg-surface rounded-xl border border-subtle">
        <div className="text-[9px] font-bold text-muted uppercase mb-1">Total Cost</div>
        <div className="text-lg font-black text-safe">${result?.total_cost_usd?.toLocaleString()}</div>
      </div>
      <div className="p-3 bg-surface rounded-xl border border-subtle">
        <div className="text-[9px] font-bold text-muted uppercase mb-1">Solver Status</div>
        <div className="text-sm font-black text-primary">{result?.optimization_status ?? 'Optimal'}</div>
      </div>
    </div>
    {result?.routing_plan?.length > 0 && (
      <div className="overflow-x-auto">
        <table className="w-full text-[10px]">
          <thead>
            <tr className="text-[9px] text-muted uppercase border-b border-subtle">
              <th className="text-left pb-2 pr-3">Origin</th>
              <th className="text-left pb-2 pr-3">Destination</th>
              <th className="text-right pb-2 pr-3">Qty (FEU)</th>
              <th className="text-right pb-2">Lane Cost</th>
            </tr>
          </thead>
          <tbody>
            {result.routing_plan.map((r: any, i: number) => (
              <tr key={i} className="border-b border-subtle/30">
                <td className="py-1.5 pr-3 font-mono text-primary">{r.origin}</td>
                <td className="pr-3 text-secondary">{r.destination}</td>
                <td className="pr-3 text-right font-mono">{r.quantity}</td>
                <td className="text-right font-mono text-safe">${r.total_lane_cost?.toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    )}
  </div>
);

const MonteCarloResult: React.FC<{ result: any }> = ({ result }) => {
  const pct = ((result?.probability_on_time ?? 0) * 100).toFixed(1);
  const isRisky = result?.risk_assessment === 'CRITICAL';
  return (
    <div className="grid grid-cols-3 gap-2">
      <div className="p-3 bg-surface rounded-xl border border-subtle">
        <div className="text-[9px] font-bold text-muted uppercase mb-1">On-Time Probability</div>
        <div className={`text-xl font-black ${isRisky ? 'text-critical' : 'text-safe'}`}>{pct}%</div>
      </div>
      <div className="p-3 bg-surface rounded-xl border border-subtle">
        <div className="text-[9px] font-bold text-muted uppercase mb-1">P95 Arrival</div>
        <div className="text-xl font-black text-primary">{result?.percentile_95_arrival_days}d</div>
      </div>
      <div className={`p-3 rounded-xl border ${isRisky ? 'bg-critical/10 border-critical/30' : 'bg-safe/10 border-safe/30'}`}>
        <div className="text-[9px] font-bold text-muted uppercase mb-1">Assessment</div>
        <div className={`text-sm font-black ${isRisky ? 'text-critical' : 'text-safe'}`}>
          {result?.risk_assessment}
        </div>
        <div className="text-[9px] text-muted mt-1">{result?.simulations_run?.toLocaleString()} simulations</div>
      </div>
    </div>
  );
};

const MEIOResult: React.FC<{ result: any }> = ({ result }) => (
  <div className="space-y-2">
    {(Array.isArray(result) ? result : []).map((node: any) => (
      <div key={node.node_id} className="flex items-center justify-between p-3 bg-surface rounded-xl border border-subtle">
        <span className="text-[10px] font-mono font-black text-primary">{node.node_id}</span>
        <div className="flex gap-4 text-[10px]">
          <div>
            <span className="text-muted">Safety stock </span>
            <span className="font-black text-primary">{node.optimal_safety_stock?.toLocaleString()}</span>
          </div>
          <div>
            <span className="text-muted">Total inv </span>
            <span className="font-black text-safe">{node.optimal_total_inventory?.toLocaleString()}</span>
          </div>
          <div>
            <span className="text-muted">Z </span>
            <span className="font-mono text-secondary">{node.z_score_used}</span>
          </div>
        </div>
      </div>
    ))}
  </div>
);

// ── Panels ────────────────────────────────────────────────────────────────────

const DelayPredictionPanel: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [result, setResult]   = useState<any>(null);
  const [error, setError]     = useState('');
  const rows = [
    { shipment_id: 'SYS-1001', route: 'CN-US', order_value: 500000, credit_days: 30, carrier: 'COSCO' },
    { shipment_id: 'SYS-1002', route: 'EU-US', order_value: 210000, credit_days: 45, carrier: 'Maersk' },
    { shipment_id: 'SYS-1003', route: 'IN-AE', order_value: 85000,  credit_days: 30, carrier: 'MSC' },
  ];

  const run = async () => {
    setLoading(true); setError(''); setResult(null);
    try { setResult(await apiService.predictDelay(rows)); }
    catch (e: any) { setError(e.message); }
    finally { setLoading(false); }
  };

  const delayColor = (d: number) => d > 4 ? 'text-critical' : d > 2 ? 'text-warning' : 'text-safe';

  return (
    <Section title="Batch Delay Prediction" sub="POST /api/v1/predict/delay — XGBoost regressor across shipment portfolio" badge="ML">
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
                    +{p.predicted_delay_days.toFixed(1)}d
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

const NetworkOptimizerPanel: React.FC = () => {
  const [loading, setLoading]     = useState(false);
  const [response, setResponse]   = useState<JobResponse | null>(null);
  const [error, setError]         = useState('');

  const demoPayload = {
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

  const run = async () => {
    setLoading(true); setError(''); setResponse(null);
    try { setResponse(await apiService.optimizeNetwork(demoPayload) as JobResponse); }
    catch (e: any) { setError(e.message); }
    finally { setLoading(false); }
  };

  return (
    <Section title="MILP Network Routing Optimizer" sub="POST /optimization/network — Minimum cost flow with capacity constraints" badge="MILP">
      <div className="mb-3 text-[10px] text-secondary grid grid-cols-2 gap-4">
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
      <button className="btn-primary text-xs flex items-center gap-2" onClick={run} disabled={loading}>
        {loading ? <Loader2 size={12} className="animate-spin" /> : <Zap size={12} />}
        Dispatch to MILP Solver
      </button>
      {response && (
        <JobPoller response={response} resultRenderer={r => <NetworkResult result={r} />} />
      )}
      {error && <Err msg={error} />}
    </Section>
  );
};

const MonteCarloPanel: React.FC = () => {
  const [loading, setLoading]     = useState(false);
  const [response, setResponse]   = useState<JobResponse | null>(null);
  const [error, setError]         = useState('');
  const [simulations, setSimulations] = useState(10000);
  const [targetDays, setTargetDays]   = useState(21);

  // Fields match the backend normalization: mean_days / std_days
  const legs = [
    { mean_days: 14.0, std_days: 2.5, cost_per_day: 3200 },
    { mean_days: 3.0,  std_days: 1.0, cost_per_day: 850  },
    { mean_days: 2.0,  std_days: 0.5, cost_per_day: 420  },
  ];

  const run = async () => {
    setLoading(true); setError(''); setResponse(null);
    try { setResponse(await apiService.runMonteCarloRisk(legs, targetDays, simulations) as JobResponse); }
    catch (e: any) { setError(e.message); }
    finally { setLoading(false); }
  };

  return (
    <Section title="Monte Carlo Risk Simulation" sub="POST /optimization/monte_carlo_risk — Probabilistic CVaR across N scenarios" badge="Stochastic">
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
      {response && (
        <JobPoller response={response} resultRenderer={r => <MonteCarloResult result={r} />} />
      )}
      {error && <Err msg={error} />}
    </Section>
  );
};

const InventoryQueuePanel: React.FC = () => {
  const [loading, setLoading]     = useState(false);
  const [response, setResponse]   = useState<JobResponse | null>(null);
  const [error, setError]         = useState('');
  const [serviceLevel, setServiceLevel] = useState(0.95);

  const nodes = [
    { node_id: 'DC-EAST',  demand_mean: 450, demand_std: 80,  lead_time_days: 7,  holding_cost: 12 },
    { node_id: 'DC-WEST',  demand_mean: 320, demand_std: 60,  lead_time_days: 10, holding_cost: 11 },
    { node_id: 'HUB-MAIN', demand_mean: 900, demand_std: 140, lead_time_days: 3,  holding_cost: 8  },
  ];

  const run = async () => {
    setLoading(true); setError(''); setResponse(null);
    try { setResponse(await apiService.optimizeInventoryQueue(nodes, serviceLevel) as JobResponse); }
    catch (e: any) { setError(e.message); }
    finally { setLoading(false); }
  };

  return (
    <Section title="Inventory MEIO Optimizer" sub="POST /optimization/inventory_meio — Safety stock across distribution network" badge="MEIO">
      <div className="mb-3 text-[10px] space-y-1">
        {nodes.map(n => (
          <div key={n.node_id} className="flex items-center justify-between p-2 bg-surface rounded-lg border border-subtle">
            <span className="font-mono font-black text-primary">{n.node_id}</span>
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
        Optimize Inventory
      </button>
      {response && (
        <JobPoller response={response} resultRenderer={r => <MEIOResult result={r} />} />
      )}
      {error && <Err msg={error} />}
    </Section>
  );
};

const EFIOptimizerPanel: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [result, setResult]   = useState<any>(null);
  const [error, setError]     = useState('');
  const [riskAppetite, setRiskAppetite] = useState('BALANCED');
  const [availableCash, setAvailableCash] = useState(1000000);

  const candidateMatrix = [
    [
      { shipment_id: 'SYS-1001', action: 'HOLD',         efi: 12400, cost: 0     },
      { shipment_id: 'SYS-1001', action: 'REROUTE_AIR',  efi: 18200, cost: 14000 },
      { shipment_id: 'SYS-1001', action: 'REROUTE_RAIL', efi: 15100, cost: 5200  },
    ],
    [
      { shipment_id: 'SYS-1002', action: 'HOLD',         efi: 8200,  cost: 0    },
      { shipment_id: 'SYS-1002', action: 'EXPEDITE',     efi: 11600, cost: 8800 },
      { shipment_id: 'SYS-1002', action: 'REROUTE_RAIL', efi: 9800,  cost: 3100 },
    ],
  ];

  const run = async () => {
    setLoading(true); setError(''); setResult(null);
    try { setResult(await apiService.optimizeEFI(candidateMatrix, availableCash, riskAppetite)); }
    catch (e: any) { setError(e.message); }
    finally { setLoading(false); }
  };

  return (
    <Section title="EFI Portfolio Optimizer (StochasticMIP)" sub="POST /api/v1/predict/efi — Optimal action set under budget constraint" badge="MIP">
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
            <span className="font-black text-primary">{actions[0].shipment_id}:</span>
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
          <div className="space-y-1">
            {result.optimized_decisions?.map((d: any, i: number) => (
              <div key={i} className="flex items-center justify-between p-2.5 bg-surface rounded-xl border border-subtle">
                <span className="text-[10px] font-mono text-primary">{d.shipment_id}</span>
                <span className="text-[10px] font-black text-brand-primary">{d.action}</span>
                <div className="text-right">
                  <div className="text-[10px] font-black text-safe">EFI ${d.efi?.toLocaleString()}</div>
                  <div className="text-[9px] text-muted">Cost ${d.cost?.toLocaleString()}</div>
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

// ── Main page ─────────────────────────────────────────────────────────────────

export const OptimizationPage: React.FC = () => (
  <div className="p-8 max-w-5xl mx-auto">
    <div className="mb-6">
      <h2 className="text-2xl font-black text-primary tracking-tighter">Optimization Engine (POE)</h2>
      <p className="text-sm text-secondary mt-1">
        Mathematical solvers, stochastic simulation, and ML prediction pipelines.
        Results render immediately when Celery is unavailable (inline mode) or poll every 2s from the job queue.
      </p>
    </div>
    <DelayPredictionPanel />
    <EFIOptimizerPanel />
    <NetworkOptimizerPanel />
    <MonteCarloPanel />
    <InventoryQueuePanel />
  </div>
);
