import React, { useState } from 'react';
import { Loader2, Zap, AlertTriangle, CheckCircle, ChevronDown, ChevronUp } from 'lucide-react';
import { apiService } from '../../services/api';

// ── helpers ──────────────────────────────────────────────────────────────────
const Section: React.FC<{ title: string; sub: string; children: React.ReactNode }> = ({ title, sub, children }) => {
  const [open, setOpen] = useState(true);
  return (
    <div className="glass-panel p-5 mb-6 rounded-2xl border border-subtle">
      <button className="flex justify-between items-center w-full mb-4" onClick={() => setOpen(!open)}>
        <div className="text-left">
          <h3 className="text-sm font-black text-primary uppercase tracking-tight">{title}</h3>
          <p className="text-[10px] text-muted mt-0.5">{sub}</p>
        </div>
        {open ? <ChevronUp size={16} className="text-muted" /> : <ChevronDown size={16} className="text-muted" />}
      </button>
      {open && children}
    </div>
  );
};

const ResultBox: React.FC<{ data: any }> = ({ data }) => (
  <pre className="mt-3 p-3 bg-surface rounded-xl border border-subtle text-[10px] text-secondary overflow-auto max-h-64">
    {JSON.stringify(data, null, 2)}
  </pre>
);

const Err: React.FC<{ msg: string }> = ({ msg }) => (
  <div className="mt-3 flex items-center gap-2 text-critical text-[11px] p-3 bg-critical/10 rounded-xl border border-critical/30">
    <AlertTriangle size={14} /> {msg}
  </div>
);

// ── Carbon Tax ────────────────────────────────────────────────────────────────
const CarbonTaxPanel: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState('');
  const [form, setForm] = useState({
    shipment_id: 'SHIP-001', route: 'CN-US', carrier: 'COSCO',
    order_value: 500000, total_cost: 425000, weight_tons: 18,
  });

  const run = async () => {
    setLoading(true); setError(''); setResult(null);
    try {
      const res = await apiService.getCarbonTax([form]);
      setResult(res);
    } catch (e: any) { setError(e.message); }
    finally { setLoading(false); }
  };

  return (
    <Section title="Carbon Tax Engine" sub="POST /enterprise/carbon-tax — Scope 3 emissions + CBAM tax liability">
      <div className="grid grid-cols-3 gap-3 mb-3">
        {['shipment_id', 'route', 'carrier'].map(k => (
          <div key={k}>
            <label className="text-[9px] font-bold text-muted uppercase block mb-1">{k}</label>
            <input className="w-full bg-surface border border-subtle rounded-lg px-3 py-2 text-xs text-primary"
              value={(form as any)[k]} onChange={e => setForm(f => ({ ...f, [k]: e.target.value }))} />
          </div>
        ))}
        {['order_value', 'total_cost', 'weight_tons'].map(k => (
          <div key={k}>
            <label className="text-[9px] font-bold text-muted uppercase block mb-1">{k}</label>
            <input type="number" className="w-full bg-surface border border-subtle rounded-lg px-3 py-2 text-xs text-primary"
              value={(form as any)[k]} onChange={e => setForm(f => ({ ...f, [k]: parseFloat(e.target.value) }))} />
          </div>
        ))}
      </div>
      <button className="btn-primary text-xs flex items-center gap-2" onClick={run} disabled={loading}>
        {loading ? <Loader2 size={12} className="animate-spin" /> : <Zap size={12} />}
        Calculate Emissions & CBAM Tax
      </button>
      {result && (
        <div className="mt-3 grid grid-cols-3 gap-3">
          {result.map((r: any) => (
            <div key={r.shipment_id} className="p-3 bg-surface rounded-xl border border-subtle">
              <div className="text-[9px] text-muted uppercase font-bold mb-2">{r.shipment_id}</div>
              <div className="text-lg font-black text-warning">${r.tax_liability_usd?.toLocaleString()}</div>
              <div className="text-[10px] text-secondary">CBAM Tax Liability</div>
              <div className="text-[10px] text-muted mt-1">{r.emissions_tons?.toFixed(2)} tCO₂ · {r.carrier_efficiency_rating}</div>
            </div>
          ))}
        </div>
      )}
      {error && <Err msg={error} />}
    </Section>
  );
};

// ── AR Default Predictor ──────────────────────────────────────────────────────
const ARDefaultPanel: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState('');
  const [customers, setCustomers] = useState([
    { customer_id: 'CUST-001', order_value: 250000, credit_days: 60, historical_defaults: 0, macro_economic_index: 1.0 },
    { customer_id: 'CUST-002', order_value: 80000,  credit_days: 90, historical_defaults: 2, macro_economic_index: 0.85 },
  ]);

  const run = async () => {
    setLoading(true); setError(''); setResult(null);
    try { setResult(await apiService.getARDefault(customers)); }
    catch (e: any) { setError(e.message); }
    finally { setLoading(false); }
  };

  const riskColor = (p: number) => p > 0.15 ? 'text-critical' : p > 0.05 ? 'text-warning' : 'text-safe';

  return (
    <Section title="AR Default Predictor" sub="POST /enterprise/ar-default — Invoice default probability + Expected Credit Loss">
      <div className="space-y-2 mb-3">
        {customers.map((c, i) => (
          <div key={i} className="grid grid-cols-5 gap-2">
            {(['customer_id', 'order_value', 'credit_days', 'historical_defaults', 'macro_economic_index'] as const).map(k => (
              <div key={k}>
                <label className="text-[8px] text-muted uppercase block mb-0.5">{k.replace(/_/g,' ')}</label>
                <input className="w-full bg-surface border border-subtle rounded px-2 py-1 text-[10px] text-primary"
                  value={c[k]}
                  onChange={e => setCustomers(cs => cs.map((x, j) => j === i ? { ...x, [k]: k === 'customer_id' ? e.target.value : parseFloat(e.target.value) } : x))} />
              </div>
            ))}
          </div>
        ))}
      </div>
      <button className="btn-primary text-xs flex items-center gap-2" onClick={run} disabled={loading}>
        {loading ? <Loader2 size={12} className="animate-spin" /> : <Zap size={12} />}
        Run Default Risk Analysis
      </button>
      {result && (
        <div className="mt-3 space-y-2">
          {result.map((r: any) => (
            <div key={r.customer_id} className="flex items-center justify-between p-3 bg-surface rounded-xl border border-subtle">
              <div>
                <div className="text-xs font-bold text-primary">{r.customer_id}</div>
                <div className="text-[10px] text-muted">{r.recommended_action}</div>
              </div>
              <div className="text-right">
                <div className={`text-lg font-black ${riskColor(r.probability_of_default)}`}>
                  {(r.probability_of_default * 100).toFixed(1)}%
                </div>
                <div className="text-[10px] text-secondary">ECL: ${r.expected_credit_loss?.toLocaleString()}</div>
              </div>
            </div>
          ))}
        </div>
      )}
      {error && <Err msg={error} />}
    </Section>
  );
};

// ── MEIO ──────────────────────────────────────────────────────────────────────
const MEIOPanel: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState('');
  const [skus] = useState([
    { sku: 'SKU-ELEC-001', global_inventory: 5000, wacc: 0.10, holding_cost_usd: 12000, stockout_penalty_usd: 50000 },
    { sku: 'SKU-PHARM-44', global_inventory: 2200, wacc: 0.08, holding_cost_usd: 8500,  stockout_penalty_usd: 120000 },
  ]);

  const run = async () => {
    setLoading(true); setError(''); setResult(null);
    try { setResult(await apiService.getMEIO(skus)); }
    catch (e: any) { setError(e.message); }
    finally { setLoading(false); }
  };

  return (
    <Section title="Multi-Echelon Inventory Optimizer (MEIO)" sub="POST /enterprise/meio-inventory — Optimal safety stock allocation across echelons">
      <div className="mb-3 text-[10px] text-secondary">
        <table className="w-full">
          <thead><tr className="text-muted text-[9px] uppercase border-b border-subtle">
            <th className="text-left pb-1">SKU</th><th className="text-right pb-1">Inventory</th>
            <th className="text-right pb-1">Holding $/yr</th><th className="text-right pb-1">Stockout Penalty</th>
          </tr></thead>
          <tbody>{skus.map(s => (
            <tr key={s.sku} className="border-b border-subtle/30">
              <td className="py-1 font-mono">{s.sku}</td>
              <td className="text-right">{s.global_inventory.toLocaleString()}</td>
              <td className="text-right">${s.holding_cost_usd.toLocaleString()}</td>
              <td className="text-right text-warning">${s.stockout_penalty_usd.toLocaleString()}</td>
            </tr>
          ))}</tbody>
        </table>
      </div>
      <button className="btn-primary text-xs flex items-center gap-2" onClick={run} disabled={loading}>
        {loading ? <Loader2 size={12} className="animate-spin" /> : <Zap size={12} />}
        Optimize Inventory Allocation
      </button>
      {result && <ResultBox data={result} />}
      {error && <Err msg={error} />}
    </Section>
  );
};

// ── GNN Systemic Risk ─────────────────────────────────────────────────────────
const GNNRiskPanel: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState('');
  const shipments = [
    { shipment_id: 'SYS-1001', route: 'CN-US', order_value: 500000, risk_score: 0.35 },
    { shipment_id: 'SYS-1002', route: 'CN-EU', order_value: 210000, risk_score: 0.28 },
    { shipment_id: 'SYS-1003', route: 'US-EU', order_value: 85000,  risk_score: 0.12 },
  ];

  const run = async () => {
    setLoading(true); setError(''); setResult(null);
    try { setResult(await apiService.getGNNRisk(shipments)); }
    catch (e: any) { setError(e.message); }
    finally { setLoading(false); }
  };

  return (
    <Section title="GNN Systemic Contagion Risk" sub="POST /enterprise/gnn-systemic-risk — Graph Neural Network propagated risk across portfolio">
      <p className="text-[10px] text-secondary mb-3">
        Maps how a disruption in one shipment propagates risk to connected shipments sharing routes, carriers, or customers.
      </p>
      <button className="btn-primary text-xs flex items-center gap-2" onClick={run} disabled={loading}>
        {loading ? <Loader2 size={12} className="animate-spin" /> : <Zap size={12} />}
        Run Contagion Simulation ({shipments.length} shipments)
      </button>
      {result && (
        <div className="mt-3 space-y-2">
          {(Array.isArray(result) ? result : []).map((r: any) => (
            <div key={r.shipment_id} className="flex items-center justify-between p-3 bg-surface rounded-xl border border-subtle">
              <div>
                <div className="text-xs font-bold text-primary">{r.shipment_id}</div>
                <div className="text-[10px] text-muted">
                  Original: <span className="text-warning">{(r.original_risk * 100).toFixed(1)}%</span>
                  {' → '}
                  Propagated: <span className="text-critical">{(r.propagated_risk * 100).toFixed(1)}%</span>
                </div>
              </div>
              {r.systemic_contagion_detected && (
                <span className="text-[9px] font-black uppercase px-2 py-1 bg-critical/10 text-critical rounded-full border border-critical/30">
                  Contagion Detected
                </span>
              )}
            </div>
          ))}
        </div>
      )}
      {error && <Err msg={error} />}
    </Section>
  );
};

// ── LLM Negotiator ────────────────────────────────────────────────────────────
const LLMNegotiatorPanel: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState('');
  const [form, setForm] = useState({
    supplier_id: 'SUPP-COSCO-001',
    historical_delay_variance_pct: 18.5,
    current_payment_terms: 30,
    target_payment_terms: 60,
    wacc_carrying_cost_usd: 14200,
  });

  const run = async () => {
    setLoading(true); setError(''); setResult(null);
    try { setResult(await apiService.getLLMNegotiator([form])); }
    catch (e: any) { setError(e.message); }
    finally { setLoading(false); }
  };

  return (
    <Section title="LLM Contract Negotiator" sub="POST /enterprise/llm-negotiator — AI-generated supplier negotiation strategy">
      <div className="grid grid-cols-2 gap-3 mb-3">
        {[
          ['supplier_id', 'text'],
          ['wacc_carrying_cost_usd', 'number'],
          ['current_payment_terms', 'number'],
          ['target_payment_terms', 'number'],
          ['historical_delay_variance_pct', 'number'],
        ].map(([k, t]) => (
          <div key={k}>
            <label className="text-[9px] font-bold text-muted uppercase block mb-1">{(k as string).replace(/_/g,' ')}</label>
            <input type={t as string} className="w-full bg-surface border border-subtle rounded-lg px-3 py-2 text-xs text-primary"
              value={(form as any)[k]}
              onChange={e => setForm(f => ({ ...f, [k]: t === 'number' ? parseFloat(e.target.value) : e.target.value }))} />
          </div>
        ))}
      </div>
      <button className="btn-primary text-xs flex items-center gap-2" onClick={run} disabled={loading}>
        {loading ? <Loader2 size={12} className="animate-spin" /> : <Zap size={12} />}
        Generate Negotiation Strategy
      </button>
      {result && Array.isArray(result) && result.map((r: any) => (
        <div key={r.supplier_id} className="mt-3 space-y-3">
          <div className="p-3 bg-brand-primary/5 rounded-xl border border-brand-primary/20">
            <div className="text-[9px] font-bold text-brand-primary uppercase mb-2">AI Negotiation Strategy</div>
            <p className="text-[10px] text-secondary leading-relaxed whitespace-pre-wrap">{r.strategy}</p>
          </div>
          {r.actions?.length > 0 && (
            <div className="p-3 bg-surface rounded-xl border border-subtle">
              <div className="text-[9px] font-bold text-muted uppercase mb-2">Recommended Actions</div>
              <ul className="space-y-1">
                {r.actions.map((action: string, i: number) => (
                  <li key={i} className="flex items-start gap-2 text-[10px] text-secondary">
                    <CheckCircle size={10} className="text-safe mt-0.5 shrink-0" />
                    {action}
                  </li>
                ))}
              </ul>
            </div>
          )}
          <div className="flex items-center gap-2 text-[10px] text-safe">
            <CheckCircle size={12} /> Engine: {r.llm_engine} · Status: {r.status}
          </div>
        </div>
      ))}
      {error && <Err msg={error} />}
    </Section>
  );
};

// ── Document Intelligence ─────────────────────────────────────────────────────
const DocumentIntelPanel: React.FC = () => {
  const [loading, setLoading] = useState<'gaps' | 'disputes' | null>(null);
  const [gaps, setGaps] = useState<string[] | null>(null);
  const [disputes, setDisputes] = useState<any[] | null>(null);
  const [error, setError] = useState('');

  const runGaps = async () => {
    setLoading('gaps'); setError('');
    try { setGaps(await apiService.getDocumentGaps()); }
    catch (e: any) { setError(e.message); }
    finally { setLoading(null); }
  };
  const runDisputes = async () => {
    setLoading('disputes'); setError('');
    try { setDisputes(await apiService.getDocumentDisputes()); }
    catch (e: any) { setError(e.message); }
    finally { setLoading(null); }
  };

  return (
    <Section title="Document Intelligence — Agentic Analysis" sub="GET /api/v1/documents/agentic/gaps + /disputes">
      <p className="text-[10px] text-secondary mb-3">
        Requires documents uploaded via Ingestion Studio. Gap analysis cross-references contracts against insurance policies.
        Dispute detection flags billing variances {'>'} 1%.
      </p>
      <div className="flex gap-2 mb-3">
        <button className="btn-outline text-xs flex items-center gap-2" onClick={runGaps} disabled={!!loading}>
          {loading === 'gaps' ? <Loader2 size={12} className="animate-spin" /> : <Zap size={12} />}
          Detect Coverage Gaps
        </button>
        <button className="btn-outline text-xs flex items-center gap-2" onClick={runDisputes} disabled={!!loading}>
          {loading === 'disputes' ? <Loader2 size={12} className="animate-spin" /> : <Zap size={12} />}
          Detect Billing Disputes
        </button>
      </div>
      {gaps !== null && (
        <div className="mt-2">
          <div className="text-[9px] font-bold text-muted uppercase mb-2">Coverage Gaps ({gaps.length})</div>
          {gaps.length === 0
            ? <div className="text-[10px] text-safe flex items-center gap-2"><CheckCircle size={12} />No gaps detected — upload contracts + insurance docs first.</div>
            : gaps.map((g, i) => <div key={i} className="text-[10px] text-warning p-2 bg-warning/5 rounded mb-1">{g}</div>)
          }
        </div>
      )}
      {disputes !== null && (
        <div className="mt-2">
          <div className="text-[9px] font-bold text-muted uppercase mb-2">Billing Disputes ({disputes.length})</div>
          {disputes.length === 0
            ? <div className="text-[10px] text-safe flex items-center gap-2"><CheckCircle size={12} />No disputes — upload invoices + contracts first.</div>
            : <ResultBox data={disputes} />
          }
        </div>
      )}
      {error && <Err msg={error} />}
    </Section>
  );
};

// ── Main page ─────────────────────────────────────────────────────────────────
export const EnterpriseModulesPage: React.FC = () => (
  <div className="p-8 max-w-5xl mx-auto">
    <div className="mb-6">
      <h2 className="text-2xl font-black text-primary tracking-tighter">Enterprise AI Modules</h2>
      <p className="text-sm text-secondary mt-1">
        Advanced financial intelligence pipelines — Pillars 7–12 of the Fiscalogix engine.
      </p>
    </div>
    <CarbonTaxPanel />
    <ARDefaultPanel />
    <MEIOPanel />
    <GNNRiskPanel />
    <LLMNegotiatorPanel />
    <DocumentIntelPanel />
  </div>
);
