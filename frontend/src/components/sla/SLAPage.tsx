import React, { useRef, useState } from 'react';
import {
  AlertTriangle, CheckCircle, ChevronDown, ChevronUp,
  FileText, Shield, TrendingDown, Upload, Zap
} from 'lucide-react';
import { API_BASE_URL } from '../../services/api';
import './SLAPage.css';

// ── Types ─────────────────────────────────────────────────────────────────────

interface SLAClause {
  clause_type:         string;
  raw_text:            string;
  section_context:     string;
  value:               number | null;
  unit:                string;
  currency:            string;
  confidence:          'HIGH' | 'MEDIUM' | 'LOW';
  bottleneck_severity: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW' | 'NONE';
  bottleneck_reason:   string;
}

interface SLAParseResponse {
  total_clauses:         number;
  critical_count:        number;
  high_risk_count:       number;
  overall_confidence:    string;
  penalty_rate:          number | null;
  flat_fee_per_day:      number | null;
  force_majeure_applies: boolean;
  cap_limit:             number | null;
  clauses:               SLAClause[];
  bottleneck_clauses:    SLAClause[];
  llm_assisted:          boolean;
}

interface SLAPenaltyDetail {
  financial_penalty:  number;
  effective_delay:    number;
  grace_days_applied: number;
  contract_type:      string;
  otif_breach_level:  string;
  otif_multiplier:    number;
  penalty_source:     string;
  breach_level:       string;
}

interface SLAAnalysisResult {
  contract_text_preview: string;
  extraction:            SLAParseResponse;
  penalty:               SLAPenaltyDetail | null;
  risk_score:            number;
  severity_distribution: Record<string, number>;
  top_bottlenecks:       SLAClause[];
  processing_pipeline:   string[];
}

interface NegotiateResult {
  supplier_id:      string;
  strategy:         string;
  suggested_actions: string[];
  leverage_clauses: SLAClause[];
  penalty_summary:  any[];
  status:           string;
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function authHeader(): HeadersInit {
  const token = localStorage.getItem('access_token');
  return token ? { Authorization: `Bearer ${token}` } : {};
}

function severityColor(sev: string): string {
  return (
    sev === 'CRITICAL' ? '#dc2626' :
    sev === 'HIGH'     ? '#f97316' :
    sev === 'MEDIUM'   ? '#d97706' :
    sev === 'LOW'      ? '#059669' : '#94a3b8'
  );
}

function severityBg(sev: string): string {
  return (
    sev === 'CRITICAL' ? 'rgba(220,38,38,0.1)' :
    sev === 'HIGH'     ? 'rgba(249,115,22,0.1)' :
    sev === 'MEDIUM'   ? 'rgba(217,119,6,0.1)' :
    sev === 'LOW'      ? 'rgba(5,150,105,0.1)' : 'rgba(148,163,184,0.1)'
  );
}

function riskScoreColor(score: number): string {
  if (score <= 30) return '#059669';
  if (score <= 60) return '#d97706';
  if (score <= 80) return '#f97316';
  return '#dc2626';
}

function fmt(n: number | null, unit: string): string {
  if (n === null) return '—';
  if (unit === 'pct_per_day') return `${(n * 100).toFixed(2)}% / day`;
  if (unit === 'pct_total')   return `${(n * 100).toFixed(1)}% of total`;
  if (unit === 'pct')         return `${n}%`;
  if (unit === 'days')        return `${n} days`;
  if (unit === 'flat_per_day') return `$${n.toLocaleString()} / day`;
  if (unit === 'flat_total')   return `$${n.toLocaleString()}`;
  if (unit === 'pct_per_annum') return `${(n * 100).toFixed(2)}% p.a.`;
  return String(n);
}

function labelClauseType(t: string): string {
  return t.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
}

// ── Sub-components ────────────────────────────────────────────────────────────

const SeverityBadge: React.FC<{ sev: string }> = ({ sev }) => (
  <span
    className="sla-badge"
    style={{ color: severityColor(sev), background: severityBg(sev), borderColor: severityColor(sev) }}
  >
    {sev}
  </span>
);

const ConfidenceDot: React.FC<{ conf: string }> = ({ conf }) => {
  const color = conf === 'HIGH' ? '#059669' : conf === 'MEDIUM' ? '#d97706' : '#dc2626';
  return <span style={{ display: 'inline-block', width: 8, height: 8, borderRadius: '50%', background: color, marginRight: 6 }} />;
};

const ClauseRow: React.FC<{ clause: SLAClause }> = ({ clause }) => {
  const [open, setOpen] = useState(false);
  return (
    <div className="sla-clause-row" style={{ borderLeft: `3px solid ${severityColor(clause.bottleneck_severity)}` }}>
      <div className="sla-clause-header" onClick={() => setOpen(o => !o)}>
        <div className="sla-clause-left">
          <SeverityBadge sev={clause.bottleneck_severity} />
          <span className="sla-clause-type">{labelClauseType(clause.clause_type)}</span>
          {clause.value !== null && (
            <span className="sla-clause-value">{fmt(clause.value, clause.unit)}</span>
          )}
        </div>
        <div className="sla-clause-right">
          <ConfidenceDot conf={clause.confidence} />
          <span className="sla-clause-conf">{clause.confidence}</span>
          {open ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
        </div>
      </div>
      {open && (
        <div className="sla-clause-detail">
          <div className="sla-clause-text">"{clause.raw_text}"</div>
          {clause.bottleneck_reason && (
            <div className="sla-clause-reason">
              <AlertTriangle size={12} /> {clause.bottleneck_reason}
            </div>
          )}
          {clause.section_context && (
            <div className="sla-clause-section">Section: {clause.section_context}</div>
          )}
        </div>
      )}
    </div>
  );
};

// ── Main page ─────────────────────────────────────────────────────────────────

export const SLAPage: React.FC = () => {
  const [tab, setTab] = useState<'analyze' | 'negotiate'>('analyze');

  // Analyze state
  const fileRef         = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [dragging, setDragging]         = useState(false);
  const [loading, setLoading]           = useState(false);
  const [error, setError]               = useState<string | null>(null);
  const [result, setResult]             = useState<SLAAnalysisResult | null>(null);

  // Shipment context form
  const [orderValue, setOrderValue]     = useState('');
  const [contractType, setContractType] = useState('standard');
  const [customerTier, setCustomerTier] = useState('standard');
  const [delayDays, setDelayDays]       = useState('');
  const [otifActual, setOtifActual]     = useState('');
  const [useLlm, setUseLlm]             = useState(false);
  const [showAllClauses, setShowAllClauses] = useState(false);

  // Negotiate state
  const [supplierId, setSupplierId]         = useState('');
  const [delayVariance, setDelayVariance]   = useState('');
  const [currentTerms, setCurrentTerms]     = useState('30');
  const [targetTerms, setTargetTerms]       = useState('60');
  const [waccCost, setWaccCost]             = useState('');
  const [negLoading, setNegLoading]         = useState(false);
  const [negError, setNegError]             = useState<string | null>(null);
  const [negResult, setNegResult]           = useState<NegotiateResult | null>(null);

  // ── Analyze handlers ────────────────────────────────────────────────────────

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragging(false);
    const dropped = e.dataTransfer.files[0];
    if (dropped?.type === 'application/pdf') { setFile(dropped); setResult(null); setError(null); }
    else setError('Only PDF files are accepted.');
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (!f) return;
    setFile(f); setResult(null); setError(null);
  };

  const handleAnalyze = async () => {
    if (!file) return;
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const params = new URLSearchParams({
        use_llm:              String(useLlm),
        order_value:          orderValue || '0',
        contract_type:        contractType,
        customer_tier:        customerTier,
        predicted_delay_days: delayDays || '0',
        otif_threshold_pct:   '95',
        ...(otifActual ? { otif_actual_pct: otifActual } : {}),
      });

      const fd = new FormData();
      fd.append('file', file);

      const resp = await fetch(`${API_BASE_URL}/sla/analyze?${params}`, {
        method:  'POST',
        headers: authHeader() as Record<string, string>,
        body:    fd,
      });

      if (!resp.ok) {
        const err = await resp.json().catch(() => ({}));
        throw new Error(err.detail || `Analysis failed (${resp.status})`);
      }

      setResult(await resp.json());
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  // ── Negotiate handler ───────────────────────────────────────────────────────

  const handleNegotiate = async () => {
    if (!supplierId) { setNegError('Supplier ID is required.'); return; }
    setNegLoading(true); setNegError(null); setNegResult(null);

    try {
      const contractClauses = result?.extraction.bottleneck_clauses ?? undefined;
      const resp = await fetch(`${API_BASE_URL}/sla/negotiate`, {
        method:  'POST',
        headers: { 'Content-Type': 'application/json', ...(authHeader() as Record<string, string>) },
        body: JSON.stringify({
          supplier_data: {
            supplier_id:                     supplierId,
            historical_delay_variance_pct:   parseFloat(delayVariance) || undefined,
            current_payment_terms:           parseInt(currentTerms) || 30,
            target_payment_terms:            parseInt(targetTerms) || 60,
            wacc_carrying_cost_usd:          parseFloat(waccCost) || 0,
          },
          contract_clauses: contractClauses,
          tenant_id: 'default_tenant',
        }),
      });

      if (!resp.ok) {
        const err = await resp.json().catch(() => ({}));
        throw new Error(err.detail || `Negotiation failed (${resp.status})`);
      }
      setNegResult(await resp.json());
    } catch (e: any) {
      setNegError(e.message);
    } finally {
      setNegLoading(false);
    }
  };

  // ── Render ──────────────────────────────────────────────────────────────────

  const scoreColor = result ? riskScoreColor(result.risk_score) : '#94a3b8';
  const displayClauses = result
    ? (showAllClauses ? result.extraction.clauses : result.extraction.clauses.slice(0, 8))
    : [];

  return (
    <div className="sla-page">

      {/* Header */}
      <header className="sla-header glass-panel">
        <div className="sla-header-left">
          <Shield size={28} className="sla-header-icon" />
          <div>
            <h1 className="page-title">SLA Contract Analyser</h1>
            <p className="page-subtitle">
              Upload a contract PDF — extract penalty clauses, bottleneck triggers, and compute financial exposure in seconds.
            </p>
          </div>
        </div>
        <div className="sla-pipeline-badges">
          {['Parse', 'Extract', 'Calculate', 'Score', 'Output'].map((s, i) => (
            <React.Fragment key={s}>
              <span className="sla-pipeline-step">{s}</span>
              {i < 4 && <span className="sla-pipeline-arrow">→</span>}
            </React.Fragment>
          ))}
        </div>
      </header>

      {/* Tabs */}
      <div className="sla-tabs">
        <button className={`sla-tab-btn ${tab === 'analyze' ? 'active' : ''}`} onClick={() => setTab('analyze')}>
          <FileText size={16} /> Analyze Contract
        </button>
        <button className={`sla-tab-btn ${tab === 'negotiate' ? 'active' : ''}`} onClick={() => setTab('negotiate')}>
          <Zap size={16} /> Negotiation Brief
          {result && <span className="sla-tab-badge">Ready</span>}
        </button>
      </div>

      {/* ── Analyze Tab ── */}
      {tab === 'analyze' && (
        <div className={`sla-analyze-layout ${result ? 'has-result' : ''}`}>

          {/* Upload + context panel */}
          <div className="sla-upload-panel glass-panel">
            <h3 className="sla-panel-title">Contract Upload</h3>

            {/* Drop zone */}
            <div
              className={`sla-dropzone ${dragging ? 'dragging' : ''} ${file ? 'has-file' : ''}`}
              onDragOver={e => { e.preventDefault(); setDragging(true); }}
              onDragLeave={() => setDragging(false)}
              onDrop={handleDrop}
              onClick={() => fileRef.current?.click()}
            >
              <input ref={fileRef} type="file" accept=".pdf" hidden onChange={handleFileChange} />
              {file ? (
                <>
                  <CheckCircle size={28} color="#059669" />
                  <div className="sla-dropzone-filename">{file.name}</div>
                  <div className="sla-dropzone-size">{(file.size / 1024).toFixed(1)} KB — click to replace</div>
                </>
              ) : (
                <>
                  <Upload size={28} />
                  <div className="sla-dropzone-label">Drop contract PDF here</div>
                  <div className="sla-dropzone-sub">or click to browse · max 20 MB</div>
                </>
              )}
            </div>

            {/* Shipment context */}
            <div className="sla-form-section">
              <div className="sla-form-label">Shipment Context <span className="sla-form-hint">(optional — required for penalty amount)</span></div>

              <div className="sla-form-row">
                <div className="sla-field">
                  <label>Order Value (USD)</label>
                  <input type="number" placeholder="e.g. 250000" value={orderValue}
                    onChange={e => setOrderValue(e.target.value)} className="sla-input" />
                </div>
                <div className="sla-field">
                  <label>Delay Days</label>
                  <input type="number" placeholder="e.g. 5" value={delayDays}
                    onChange={e => setDelayDays(e.target.value)} className="sla-input" />
                </div>
              </div>

              <div className="sla-form-row">
                <div className="sla-field">
                  <label>Contract Type</label>
                  <select value={contractType} onChange={e => setContractType(e.target.value)} className="sla-input">
                    <option value="standard">Standard</option>
                    <option value="strict">Strict</option>
                    <option value="lenient">Lenient</option>
                    <option value="full_rejection">Full Rejection (Walmart)</option>
                  </select>
                </div>
                <div className="sla-field">
                  <label>Customer Tier</label>
                  <select value={customerTier} onChange={e => setCustomerTier(e.target.value)} className="sla-input">
                    <option value="enterprise">Enterprise</option>
                    <option value="strategic">Strategic</option>
                    <option value="growth">Growth</option>
                    <option value="standard">Standard</option>
                    <option value="spot">Spot</option>
                    <option value="trial">Trial</option>
                  </select>
                </div>
              </div>

              <div className="sla-form-row">
                <div className="sla-field">
                  <label>Actual OTIF % (if known)</label>
                  <input type="number" placeholder="e.g. 88" value={otifActual}
                    onChange={e => setOtifActual(e.target.value)} className="sla-input" />
                </div>
                <div className="sla-field sla-field-toggle">
                  <label>
                    <input type="checkbox" checked={useLlm} onChange={e => setUseLlm(e.target.checked)} />
                    Force LLM extraction
                  </label>
                  <span className="sla-form-hint">Slower but captures complex cross-referenced clauses</span>
                </div>
              </div>
            </div>

            {error && (
              <div className="sla-error">
                <AlertTriangle size={14} /> {error}
              </div>
            )}

            <button
              className="sla-analyze-btn"
              onClick={handleAnalyze}
              disabled={!file || loading}
            >
              {loading ? (
                <><span className="sla-spinner" /> Analysing…</>
              ) : (
                <><FileText size={16} /> Analyse Contract</>
              )}
            </button>
          </div>

          {/* Results panel */}
          {result && (
            <div className="sla-results-panel">

              {/* Risk score banner */}
              <div className="sla-risk-banner glass-panel" style={{ borderLeft: `5px solid ${scoreColor}` }}>
                <div className="sla-risk-score-block">
                  <div className="sla-risk-score-num" style={{ color: scoreColor }}>{result.risk_score}</div>
                  <div className="sla-risk-score-label">/ 100 Risk Score</div>
                </div>
                <div className="sla-risk-dist">
                  {(['CRITICAL', 'HIGH', 'MEDIUM', 'LOW'] as const).map(s => (
                    <div key={s} className="sla-risk-dist-item">
                      <div className="sla-risk-dist-num" style={{ color: severityColor(s) }}>
                        {result.severity_distribution[s] ?? 0}
                      </div>
                      <div className="sla-risk-dist-label">{s}</div>
                    </div>
                  ))}
                </div>
                <div className="sla-risk-meta">
                  <div className="sla-risk-meta-item">
                    <span>Confidence</span><strong>{result.extraction.overall_confidence}</strong>
                  </div>
                  <div className="sla-risk-meta-item">
                    <span>Total Clauses</span><strong>{result.extraction.total_clauses}</strong>
                  </div>
                  <div className="sla-risk-meta-item">
                    <span>Force Majeure</span>
                    <strong style={{ color: result.extraction.force_majeure_applies ? '#059669' : '#94a3b8' }}>
                      {result.extraction.force_majeure_applies ? 'Present' : 'Absent'}
                    </strong>
                  </div>
                  {result.extraction.llm_assisted && (
                    <div className="sla-risk-meta-item">
                      <span>Extraction</span><strong style={{ color: '#6366f1' }}>LLM-assisted</strong>
                    </div>
                  )}
                </div>
              </div>

              {/* Penalty card */}
              {result.penalty && (
                <div className="sla-penalty-card glass-panel">
                  <div className="sla-penalty-title">
                    <TrendingDown size={16} />
                    Computed Financial Penalty
                    <span className="sla-penalty-source">{result.penalty.penalty_source === 'nlp_contract' ? 'from contract' : 'tier heuristic'}</span>
                  </div>
                  <div className="sla-penalty-amount" style={{ color: severityColor(result.penalty.breach_level.toUpperCase()) }}>
                    ${result.penalty.financial_penalty.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                  </div>
                  <div className="sla-penalty-meta-row">
                    <div className="sla-penalty-meta-item">
                      <span>Effective Delay</span><strong>{result.penalty.effective_delay}d</strong>
                    </div>
                    <div className="sla-penalty-meta-item">
                      <span>Grace Applied</span><strong>{result.penalty.grace_days_applied}d</strong>
                    </div>
                    <div className="sla-penalty-meta-item">
                      <span>OTIF Breach</span>
                      <strong style={{ color: severityColor(result.penalty.otif_breach_level.toUpperCase()) }}>
                        {result.penalty.otif_breach_level} ({result.penalty.otif_multiplier}×)
                      </strong>
                    </div>
                    <div className="sla-penalty-meta-item">
                      <span>Severity</span>
                      <strong style={{ color: severityColor(result.penalty.breach_level.toUpperCase()) }}>
                        {result.penalty.breach_level.toUpperCase()}
                      </strong>
                    </div>
                  </div>
                </div>
              )}

              {/* Top bottlenecks */}
              {result.top_bottlenecks.length > 0 && (
                <div className="sla-section glass-panel">
                  <h4 className="sla-section-title"><AlertTriangle size={15} /> Top Bottleneck Clauses</h4>
                  <div className="sla-bottleneck-table">
                    <div className="sla-bottleneck-thead">
                      <div>Clause Type</div>
                      <div>Severity</div>
                      <div>Value</div>
                      <div>Risk Reason</div>
                    </div>
                    {result.top_bottlenecks.map((c, i) => (
                      <div key={i} className="sla-bottleneck-row">
                        <div className="sla-bottleneck-type">{labelClauseType(c.clause_type)}</div>
                        <div><SeverityBadge sev={c.bottleneck_severity} /></div>
                        <div className="sla-bottleneck-value">{fmt(c.value, c.unit) || '—'}</div>
                        <div className="sla-bottleneck-reason">{c.bottleneck_reason}</div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* All clauses */}
              {result.extraction.clauses.length > 0 && (
                <div className="sla-section glass-panel">
                  <h4 className="sla-section-title"><FileText size={15} /> All Extracted Clauses ({result.extraction.total_clauses})</h4>
                  <div className="sla-clauses-list">
                    {displayClauses.map((c, i) => <ClauseRow key={i} clause={c} />)}
                  </div>
                  {result.extraction.clauses.length > 8 && (
                    <button className="sla-show-more-btn" onClick={() => setShowAllClauses(v => !v)}>
                      {showAllClauses ? <><ChevronUp size={14} /> Show less</> : <><ChevronDown size={14} /> Show all {result.extraction.clauses.length} clauses</>}
                    </button>
                  )}
                </div>
              )}

              {/* Processing pipeline */}
              <div className="sla-pipeline-trace">
                {result.processing_pipeline.map((s, i) => (
                  <React.Fragment key={s}>
                    <span className="sla-trace-step"><CheckCircle size={11} /> {s}</span>
                    {i < result.processing_pipeline.length - 1 && <span className="sla-trace-arrow">›</span>}
                  </React.Fragment>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* ── Negotiate Tab ── */}
      {tab === 'negotiate' && (
        <div className="sla-negotiate-layout">
          <div className="sla-upload-panel glass-panel">
            <h3 className="sla-panel-title">Supplier Data</h3>
            {result && (
              <div className="sla-neg-prefill-notice">
                <CheckCircle size={13} color="#059669" />
                {result.extraction.bottleneck_clauses.length} bottleneck clauses from your analysis will be included automatically.
              </div>
            )}

            <div className="sla-form-section">
              <div className="sla-form-row">
                <div className="sla-field">
                  <label>Supplier ID *</label>
                  <input value={supplierId} onChange={e => setSupplierId(e.target.value)}
                    placeholder="e.g. SUPPLIER-001" className="sla-input" />
                </div>
                <div className="sla-field">
                  <label>Delay Variance (%)</label>
                  <input type="number" value={delayVariance} onChange={e => setDelayVariance(e.target.value)}
                    placeholder="e.g. 14.5" className="sla-input" />
                </div>
              </div>
              <div className="sla-form-row">
                <div className="sla-field">
                  <label>Current Payment Terms (days)</label>
                  <input type="number" value={currentTerms} onChange={e => setCurrentTerms(e.target.value)} className="sla-input" />
                </div>
                <div className="sla-field">
                  <label>Target Payment Terms (days)</label>
                  <input type="number" value={targetTerms} onChange={e => setTargetTerms(e.target.value)} className="sla-input" />
                </div>
              </div>
              <div className="sla-form-row">
                <div className="sla-field">
                  <label>WACC Carrying Cost (USD/year)</label>
                  <input type="number" value={waccCost} onChange={e => setWaccCost(e.target.value)}
                    placeholder="e.g. 48000" className="sla-input" />
                </div>
              </div>
            </div>

            {negError && <div className="sla-error"><AlertTriangle size={14} /> {negError}</div>}

            <button className="sla-analyze-btn" onClick={handleNegotiate} disabled={negLoading}>
              {negLoading ? <><span className="sla-spinner" /> Generating…</> : <><Zap size={16} /> Generate Strategy</>}
            </button>
          </div>

          {negResult && (
            <div className="sla-results-panel">
              <div className="sla-section glass-panel">
                <h4 className="sla-section-title"><Zap size={15} /> Negotiation Strategy — {negResult.supplier_id}</h4>
                <pre className="sla-strategy-text">{negResult.strategy}</pre>
              </div>

              {negResult.suggested_actions?.length > 0 && (
                <div className="sla-section glass-panel">
                  <h4 className="sla-section-title">Suggested Actions</h4>
                  <ul className="sla-actions-list">
                    {negResult.suggested_actions.map((a, i) => (
                      <li key={i}><CheckCircle size={13} color="#059669" /> {a}</li>
                    ))}
                  </ul>
                </div>
              )}

              {negResult.leverage_clauses?.length > 0 && (
                <div className="sla-section glass-panel">
                  <h4 className="sla-section-title"><AlertTriangle size={15} /> Leverage Clauses</h4>
                  {negResult.leverage_clauses.map((c, i) => <ClauseRow key={i} clause={c} />)}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
};
