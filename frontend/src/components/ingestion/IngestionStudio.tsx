import React, { useState } from 'react';
import { Upload, FileText, CheckCircle, Database, AlertTriangle, GitMerge, X } from 'lucide-react';
import { API_BASE_URL } from '../../services/api';
import './IngestionStudio.css';

interface MappingResult {
  filename: string;
  detected_domain: string;
  raw_headers: string[];
  ai_mapping_suggestions: Record<string, string>;
  nlp_penalty?: string;
}

interface IngestionResult {
  rows_ingested: number;
  nlp_extracted_penalty: string;
  calculated_rate: number;
  financial_impact: number;
}

interface FileSummary {
  filename: string;
  headers: string[];
  row_count: number;
}

interface PreviewJoinResult {
  files: FileSummary[];
  join_candidates: string[];
  recommended_join_key: string | null;
  message: string;
}

interface IngestionStudioProps {
  onNavigate?: (view: string) => void;
}

function authHeader(): HeadersInit {
  const token = localStorage.getItem('access_token');
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export const IngestionStudio: React.FC<IngestionStudioProps> = ({ onNavigate }) => {
  const [mode, setMode] = useState<'single' | 'multi'>('single');

  // ── Single-file state ────────────────────────────────────────────────────
  const [file, setFile] = useState<File | null>(null);
  const [mappingData, setMappingData] = useState<MappingResult | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [isIngesting, setIsIngesting] = useState(false);
  const [ingestResult, setIngestResult] = useState<IngestionResult | null>(null);
  const [jobId, setJobId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [elapsedSec, setElapsedSec] = useState<number | null>(null);

  // ── Multi-file state ─────────────────────────────────────────────────────
  const [multiFiles, setMultiFiles] = useState<File[]>([]);
  const [multiPdf, setMultiPdf] = useState<File | null>(null);
  const [previewData, setPreviewData] = useState<PreviewJoinResult | null>(null);
  const [selectedJoinKey, setSelectedJoinKey] = useState<string>('');
  const [isPreviewing, setIsPreviewing] = useState(false);
  const [isMerging, setIsMerging] = useState(false);

  const resetAll = () => {
    setFile(null); setMappingData(null); setIngestResult(null);
    setJobId(null); setError(null); setElapsedSec(null);
    setMultiFiles([]); setMultiPdf(null); setPreviewData(null);
    setSelectedJoinKey(''); setIsAnalyzing(false); setIsIngesting(false);
    setIsPreviewing(false); setIsMerging(false);
  };

  const switchMode = (m: 'single' | 'multi') => { resetAll(); setMode(m); };

  // ── Shared SSE poller ────────────────────────────────────────────────────
  const pollStream = async (jid: string): Promise<IngestionResult> => {
    const resp = await fetch(`${API_BASE_URL}/ingestion/status-stream/${jid}`, {
      headers: authHeader(),
    });
    if (!resp.ok || !resp.body) throw new Error(`Stream failed (${resp.status})`);

    const reader = resp.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() ?? '';
      for (const line of lines) {
        if (!line.startsWith('data: ')) continue;
        const payload = JSON.parse(line.slice(6));
        if (payload.status === 'SUCCESS') { reader.cancel(); return payload.result as IngestionResult; }
        if (payload.status === 'FAILURE' || payload.status === 'ERROR') {
          reader.cancel();
          throw new Error(payload.error || 'ETL pipeline failed.');
        }
      }
    }
    throw new Error('Stream closed without result.');
  };

  // ── Single-file handlers ─────────────────────────────────────────────────
  const handleFileDrop = (e: React.DragEvent) => {
    e.preventDefault();
    if (e.dataTransfer.files?.[0]) {
      setFile(e.dataTransfer.files[0]);
      setMappingData(null); setIngestResult(null); setError(null);
    }
  };

  const handleAnalyze = async () => {
    if (!file) return;
    setIsAnalyzing(true); setError(null);
    const formData = new FormData();
    file.name.toLowerCase().endsWith('.pdf')
      ? formData.append('pdf_file', file)
      : formData.append('csv_file', file);

    try {
      const resp = await fetch(`${API_BASE_URL}/ingestion/upload`, {
        method: 'POST', headers: authHeader(), body: formData,
      });
      if (!resp.ok) {
        const err = await resp.json().catch(() => ({}));
        throw new Error(err.detail || `Upload failed (${resp.status})`);
      }
      const data = await resp.json();
      if (data.status === 'completed' && data.result) {
        const result = data.result as IngestionResult;
        setIngestResult(result);
        setMappingData({
          filename: file.name,
          detected_domain: data.detected_domain || 'Supply Chain',
          raw_headers: data.heuristic_mapping ? Object.keys(data.heuristic_mapping) : [],
          ai_mapping_suggestions: data.heuristic_mapping || {},
          nlp_penalty: result.nlp_extracted_penalty,
        });
        return;
      }
      setJobId(data.job_id);
      setMappingData({
        filename: file.name,
        detected_domain: data.detected_domain || 'Supply Chain',
        raw_headers: data.heuristic_mapping ? Object.keys(data.heuristic_mapping) : [],
        ai_mapping_suggestions: data.heuristic_mapping || {},
      });
    } catch (e: any) {
      setError(e.message || 'Upload failed.');
    } finally {
      setIsAnalyzing(false);
    }
  };

  const handleIngest = async () => {
    if (!jobId) return;
    setIsIngesting(true); setError(null);
    const t0 = Date.now();
    try {
      const result = await pollStream(jobId);
      setElapsedSec(Math.round((Date.now() - t0) / 1000));
      setIngestResult(result);
    } catch (e: any) {
      setError(e.message || 'Connection failed.');
    } finally {
      setIsIngesting(false);
    }
  };

  // ── Multi-file handlers ──────────────────────────────────────────────────
  const handleMultiDrop = (e: React.DragEvent) => {
    e.preventDefault();
    const dropped = Array.from(e.dataTransfer.files);
    const csvs = dropped.filter(f => f.name.endsWith('.csv'));
    const pdf  = dropped.find(f => f.name.endsWith('.pdf'));
    if (csvs.length) setMultiFiles(prev => [...prev, ...csvs].slice(0, 5));
    if (pdf) setMultiPdf(pdf);
    setPreviewData(null); setSelectedJoinKey(''); setError(null);
  };

  const removeMultiFile = (idx: number) => {
    setMultiFiles(prev => prev.filter((_, i) => i !== idx));
    setPreviewData(null); setSelectedJoinKey('');
  };

  const handlePreviewJoin = async () => {
    if (multiFiles.length < 2) { setError('Add at least 2 CSV files to preview the join.'); return; }
    setIsPreviewing(true); setError(null);
    const formData = new FormData();
    multiFiles.forEach(f => formData.append('files', f));
    try {
      const resp = await fetch(`${API_BASE_URL}/ingestion/preview_join`, {
        method: 'POST', headers: authHeader(), body: formData,
      });
      if (!resp.ok) {
        const err = await resp.json().catch(() => ({}));
        throw new Error(err.detail || `Preview failed (${resp.status})`);
      }
      const data: PreviewJoinResult = await resp.json();
      setPreviewData(data);
      setSelectedJoinKey(data.recommended_join_key ?? '');
    } catch (e: any) {
      setError(e.message);
    } finally {
      setIsPreviewing(false);
    }
  };

  const handleMergeIngest = async () => {
    if (!selectedJoinKey) { setError('Select a join key first.'); return; }
    setIsMerging(true); setError(null);
    const formData = new FormData();
    multiFiles.forEach(f => formData.append('files', f));
    if (multiPdf) formData.append('pdf_file', multiPdf);
    formData.append('join_key', selectedJoinKey);
    const t0 = Date.now();
    try {
      const resp = await fetch(`${API_BASE_URL}/ingestion/upload_multi`, {
        method: 'POST', headers: authHeader(), body: formData,
      });
      if (!resp.ok) {
        const err = await resp.json().catch(() => ({}));
        throw new Error(err.detail || `Merge failed (${resp.status})`);
      }
      const data = await resp.json();
      if (data.status === 'completed' && data.result) {
        setElapsedSec(Math.round((Date.now() - t0) / 1000));
        setIngestResult(data.result as IngestionResult);
        return;
      }
      const result = await pollStream(data.job_id);
      setElapsedSec(Math.round((Date.now() - t0) / 1000));
      setIngestResult(result);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setIsMerging(false);
    }
  };

  const fmtCurrency = (n: number) =>
    `$${Math.abs(n).toLocaleString('en-US', { maximumFractionDigits: 0 })}`;

  return (
    <div className="ingestion-studio p-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <Database size={24} className="text-brand-primary" /> Financial Risk Engine — Data Onboarding
        </h1>
        <p className="text-secondary mt-1">
          Drop your ERP export or carrier contract — the engine maps fields, extracts SLA penalty clauses,
          and returns your capital at risk in minutes.
        </p>
      </div>

      {/* Mode toggle */}
      {!ingestResult && (
        <div className="flex gap-2 mb-6">
          <button
            onClick={() => switchMode('single')}
            className={`flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-bold border transition-colors ${
              mode === 'single'
                ? 'bg-brand-primary text-white border-brand-primary'
                : 'bg-surface border-subtle text-secondary hover:text-primary'
            }`}
          >
            <Upload size={14} /> Single File
          </button>
          <button
            onClick={() => switchMode('multi')}
            className={`flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-bold border transition-colors ${
              mode === 'multi'
                ? 'bg-brand-primary text-white border-brand-primary'
                : 'bg-surface border-subtle text-secondary hover:text-primary'
            }`}
          >
            <GitMerge size={14} /> Multi-File Join
          </button>
        </div>
      )}

      {error && (
        <div className="mb-4 flex items-center gap-2 text-critical text-sm p-3 bg-critical/10 rounded-xl border border-critical/30">
          <AlertTriangle size={16} /> {error}
        </div>
      )}

      {/* ── SINGLE FILE FLOW ─────────────────────────────────────────────── */}
      {mode === 'single' && (
        <>
          {!mappingData && !ingestResult && (
            <div className="step-container glass-panel p-6 mb-4">
              <h2 className="step-title font-bold text-lg mb-4">Step 1: Drop Your Data</h2>
              <div className="upload-dropzone" onDragOver={e => e.preventDefault()} onDrop={handleFileDrop}>
                <Upload size={48} className="text-tertiary mb-4" />
                <h3>Drag & Drop SAP/Oracle CSV or Carrier PDF</h3>
                <p>No ETL configuration required.</p>
                <input type="file" onChange={e => setFile(e.target.files?.[0] || null)} />
                {file && (
                  <div className="selected-file mt-4">
                    <FileText size={16} /> <strong>{file.name}</strong>
                    <button className="btn-primary mt-4 w-full pulse" onClick={handleAnalyze} disabled={isAnalyzing}>
                      {isAnalyzing ? 'Parsing & Mapping Fields...' : 'Run Field Mapping & NLP Parse'}
                    </button>
                  </div>
                )}
              </div>
            </div>
          )}

          {mappingData && !ingestResult && (
            <div className="step-container glass-panel p-6 mb-4">
              <div className="mapping-header mb-4">
                <div className="flex justify-between items-center">
                  <h2 className="step-title font-bold text-lg">Step 2: Stochastic Field Mapping</h2>
                  <span className="badge badge-primary bg-brand-primary text-white px-3 py-1 rounded-full text-xs">
                    Domain: {mappingData.detected_domain}
                  </span>
                </div>
                <p className="text-sm text-secondary mt-2">Fields auto-normalised to Fiscalogix 13-Pillar Schema.</p>
              </div>
              {mappingData.raw_headers.length > 0 && (
                <table className="mapping-table w-full mb-6">
                  <thead><tr><th>Raw Customer Header</th><th>Standardised Token</th></tr></thead>
                  <tbody>
                    {mappingData.raw_headers.slice(0, 5).map((rh, idx) => {
                      const target = mappingData.ai_mapping_suggestions[rh];
                      return (
                        <tr key={idx}>
                          <td className="font-mono text-xs">{rh}</td>
                          <td>
                            <span className={`badge ${target === 'UNMAPPED_DISCARD' ? 'badge-warning' : 'badge-primary'}`}>
                              {target || '—'}
                            </span>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              )}
              <div className="contract-parsing-block p-4 mb-6" style={{ background: 'rgba(255,255,255,0.02)', borderLeft: '3px solid #60a5fa' }}>
                <h4 className="font-bold text-sm text-blue-400 mb-2">NLP Contract Parse Result:</h4>
                <p className="text-sm text-secondary">
                  {mappingData.nlp_penalty ?? 'Awaiting ETL completion — penalty clause will be extracted from the uploaded PDF.'}
                </p>
              </div>
              <div className="flex justify-end gap-3">
                <button className="btn-outline" onClick={() => setMappingData(null)}>Cancel</button>
                {jobId ? (
                  <button className="btn-primary pulse" onClick={handleIngest} disabled={isIngesting}>
                    {isIngesting ? 'Processing...' : 'Confirm & Run Financial Engine'}
                  </button>
                ) : (
                  <button className="btn-primary" disabled>Processing inline...</button>
                )}
              </div>
            </div>
          )}
        </>
      )}

      {/* ── MULTI-FILE JOIN FLOW ─────────────────────────────────────────── */}
      {mode === 'multi' && !ingestResult && (
        <>
          {/* Step 1: Drop files */}
          <div className="step-container glass-panel p-6 mb-4">
            <h2 className="step-title font-bold text-lg mb-1">Step 1: Add Your Files</h2>
            <p className="text-xs text-secondary mb-4">
              Drop 2–5 CSVs (e.g. shipment ops + financials + customer master) and optionally a carrier PDF.
              The engine will find the common join column.
            </p>

            <div
              className="upload-dropzone"
              onDragOver={e => e.preventDefault()}
              onDrop={handleMultiDrop}
            >
              <GitMerge size={40} className="text-tertiary mb-3" />
              <h3>Drag & Drop Multiple CSVs Here</h3>
              <p>Up to 5 CSV files + 1 optional PDF</p>
              <input
                type="file"
                multiple
                accept=".csv,.pdf"
                onChange={e => {
                  const picked = Array.from(e.target.files ?? []);
                  const csvs = picked.filter(f => f.name.endsWith('.csv'));
                  const pdf  = picked.find(f => f.name.endsWith('.pdf'));
                  if (csvs.length) setMultiFiles(prev => [...prev, ...csvs].slice(0, 5));
                  if (pdf) setMultiPdf(pdf);
                  setPreviewData(null); setSelectedJoinKey('');
                }}
              />
            </div>

            {/* File list */}
            {(multiFiles.length > 0 || multiPdf) && (
              <div className="mt-4 space-y-2">
                {multiFiles.map((f, i) => (
                  <div key={i} className="flex items-center justify-between p-2 rounded-lg bg-surface border border-subtle">
                    <div className="flex items-center gap-2 text-sm">
                      <FileText size={14} className="text-brand-primary" />
                      <span className="font-mono">{f.name}</span>
                      <span className="text-xs text-muted">({(f.size / 1024).toFixed(0)} KB)</span>
                    </div>
                    <button onClick={() => removeMultiFile(i)} className="text-muted hover:text-critical transition-colors">
                      <X size={14} />
                    </button>
                  </div>
                ))}
                {multiPdf && (
                  <div className="flex items-center justify-between p-2 rounded-lg bg-brand-primary/5 border border-brand-primary/20">
                    <div className="flex items-center gap-2 text-sm">
                      <FileText size={14} className="text-brand-primary" />
                      <span className="font-mono">{multiPdf.name}</span>
                      <span className="text-xs text-muted">SLA Contract</span>
                    </div>
                    <button onClick={() => setMultiPdf(null)} className="text-muted hover:text-critical transition-colors">
                      <X size={14} />
                    </button>
                  </div>
                )}
              </div>
            )}

            {multiFiles.length >= 2 && (
              <button
                className="btn-primary w-full mt-4"
                onClick={handlePreviewJoin}
                disabled={isPreviewing}
              >
                {isPreviewing ? 'Analysing Files...' : 'Preview Join Columns'}
              </button>
            )}
          </div>

          {/* Step 2: Pick join key */}
          {previewData && (
            <div className="step-container glass-panel p-6 mb-4">
              <h2 className="step-title font-bold text-lg mb-1">Step 2: Select Join Key</h2>
              <p className="text-xs text-secondary mb-4">{previewData.message}</p>

              {/* Per-file summary */}
              <div className="grid gap-3 mb-5" style={{ gridTemplateColumns: `repeat(${Math.min(previewData.files.length, 3)}, 1fr)` }}>
                {previewData.files.map((f, i) => (
                  <div key={i} className="p-3 rounded-xl bg-surface border border-subtle">
                    <div className="text-[10px] font-bold text-muted uppercase mb-1 truncate">{f.filename}</div>
                    <div className="text-lg font-black text-primary">{f.row_count.toLocaleString()} rows</div>
                    <div className="text-[9px] text-muted mt-1 font-mono truncate">
                      {f.headers.slice(0, 4).join(', ')}{f.headers.length > 4 ? ` +${f.headers.length - 4}` : ''}
                    </div>
                  </div>
                ))}
              </div>

              {previewData.join_candidates.length > 0 ? (
                <>
                  <label className="block text-[10px] font-bold text-muted uppercase mb-2">Join On Column</label>
                  <select
                    className="w-full p-2 rounded-lg bg-surface border border-subtle text-sm font-mono mb-4"
                    value={selectedJoinKey}
                    onChange={e => setSelectedJoinKey(e.target.value)}
                  >
                    {previewData.join_candidates.map(c => (
                      <option key={c} value={c}>{c}{c === previewData.recommended_join_key ? ' (recommended)' : ''}</option>
                    ))}
                  </select>
                </>
              ) : (
                <div className="p-3 bg-critical/10 border border-critical/30 rounded-xl text-sm text-critical mb-4">
                  No common columns found between files. Ensure all files share a shipment ID or PO number column.
                </div>
              )}

              <div className="flex justify-end gap-3">
                <button className="btn-outline" onClick={() => setPreviewData(null)}>Back</button>
                <button
                  className="btn-primary"
                  onClick={handleMergeIngest}
                  disabled={isMerging || !selectedJoinKey}
                >
                  {isMerging ? 'Merging & Ingesting...' : `Merge on "${selectedJoinKey}" & Run Engine`}
                </button>
              </div>
            </div>
          )}
        </>
      )}

      {/* ── STEP 3: RESULT (shared) ──────────────────────────────────────── */}
      {ingestResult && (
        <div
          className="step-container glass-panel p-6 text-center animate-fade-in"
          style={{ border: '1px solid #4ade80', background: 'rgba(74, 222, 128, 0.05)' }}
        >
          <CheckCircle size={64} className="text-safe mx-auto mb-4" />
          <h2 className="text-2xl font-bold mb-2">Financial Insight Ready</h2>
          {elapsedSec !== null && (
            <p className="text-xs text-secondary mb-4">Total processing time: {elapsedSec}s</p>
          )}

          <div className="grid grid-cols-3 gap-4 my-6 text-left">
            <div className="p-4 rounded-xl bg-surface border border-subtle">
              <div className="text-[10px] text-muted uppercase font-bold mb-1">Shipments Processed</div>
              <div className="text-2xl font-black text-primary">{ingestResult.rows_ingested.toLocaleString()}</div>
            </div>
            <div className="p-4 rounded-xl bg-surface border border-subtle">
              <div className="text-[10px] text-muted uppercase font-bold mb-1">SLA Penalty Rate</div>
              <div className="text-2xl font-black text-warning">
                {ingestResult.calculated_rate > 0
                  ? `${(ingestResult.calculated_rate * 100).toFixed(1)}%/day`
                  : 'Force Majeure — Waived'}
              </div>
            </div>
            <div className="p-4 rounded-xl" style={{ background: 'rgba(248,113,113,0.1)', border: '1px solid #f87171' }}>
              <div className="text-[10px] text-red-400 uppercase font-bold mb-1">Capital at Risk</div>
              <div className="text-2xl font-black text-red-500">
                {ingestResult.financial_impact > 0 ? fmtCurrency(ingestResult.financial_impact) : 'Calculating...'}
              </div>
            </div>
          </div>

          <div className="p-4 rounded-xl text-left mb-6" style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid #334155' }}>
            <div className="text-[10px] text-muted uppercase font-bold mb-1">Contract Extract</div>
            <p className="text-sm text-secondary">{ingestResult.nlp_extracted_penalty}</p>
          </div>

          <div className="flex justify-center gap-3">
            <button className="btn-outline" onClick={resetAll}>Upload More Data</button>
            <button className="btn-primary" onClick={() => onNavigate?.('recovery')}>
              Proceed to Recovery Dashboard
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
