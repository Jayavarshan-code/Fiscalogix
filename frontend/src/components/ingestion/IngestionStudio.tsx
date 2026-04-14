import React, { useState } from 'react';
import { Upload, FileText, CheckCircle, Database, AlertTriangle } from 'lucide-react';
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

interface IngestionStudioProps {
  onNavigate?: (view: string) => void;
}

function authHeader(): HeadersInit {
  const token = localStorage.getItem('access_token');
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export const IngestionStudio: React.FC<IngestionStudioProps> = ({ onNavigate }) => {
  const [file, setFile] = useState<File | null>(null);
  const [mappingData, setMappingData] = useState<MappingResult | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [isIngesting, setIsIngesting] = useState(false);
  const [ingestResult, setIngestResult] = useState<IngestionResult | null>(null);
  const [jobId, setJobId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [startTime, setStartTime] = useState<number | null>(null);
  const [elapsedSec, setElapsedSec] = useState<number | null>(null);

  const handleFileDrop = (e: React.DragEvent) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      setFile(e.dataTransfer.files[0]);
      setMappingData(null);
      setIngestResult(null);
      setError(null);
    }
  };

  const handleAnalyze = async () => {
    if (!file) return;
    setIsAnalyzing(true);
    setError(null);
    setStartTime(Date.now());

    const formData = new FormData();
    if (file.name.toLowerCase().endsWith('.pdf')) {
      formData.append('pdf_file', file);
    } else {
      formData.append('csv_file', file);
    }

    try {
      const resp = await fetch(`${API_BASE_URL}/ingestion/upload`, {
        method: 'POST',
        headers: authHeader(),
        body: formData,
      });

      if (!resp.ok) {
        const err = await resp.json().catch(() => ({}));
        throw new Error(err.detail || `Upload failed (${resp.status})`);
      }

      const data = await resp.json();

      // Inline sync response (Celery unavailable) — result is ready immediately
      if (data.status === 'completed' && data.result) {
        const result = data.result as IngestionResult;
        setElapsedSec(Math.round((Date.now() - Date.now()) / 1000));
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

      // Async Celery path — store job_id, show mapping, wait for user to confirm
      setJobId(data.job_id);
      setMappingData({
        filename: file.name,
        detected_domain: data.detected_domain || 'Supply Chain',
        raw_headers: data.heuristic_mapping ? Object.keys(data.heuristic_mapping) : [],
        ai_mapping_suggestions: data.heuristic_mapping || {},
      });
    } catch (e: any) {
      setError(e.message || 'Upload failed. Ensure you are logged in.');
    } finally {
      setIsAnalyzing(false);
    }
  };

  const handleIngest = async () => {
    if (!jobId) return;
    setIsIngesting(true);
    setError(null);

    const t0 = Date.now();
    const interval = setInterval(async () => {
      try {
        const resp = await fetch(`${API_BASE_URL}/ingestion/status/${jobId}`, {
          headers: authHeader(),
        });
        const jobStatus = await resp.json();

        if (jobStatus.status === 'SUCCESS') {
          clearInterval(interval);
          setElapsedSec(Math.round((Date.now() - t0) / 1000));
          setIngestResult(jobStatus.result as IngestionResult);
          setIsIngesting(false);
        } else if (jobStatus.status === 'FAILURE') {
          clearInterval(interval);
          setError('ETL pipeline failed. Check worker logs for details.');
          setIsIngesting(false);
        }
      } catch (e) {
        clearInterval(interval);
        setError('Status poll failed. Check your connection.');
        setIsIngesting(false);
      }
    }, 2000);
  };

  const fmtCurrency = (n: number) =>
    `$${Math.abs(n).toLocaleString('en-US', { maximumFractionDigits: 0 })}`;

  return (
    <div className="ingestion-studio p-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <Database size={24} className="text-brand-primary" /> Onboarding: 30-Minute TTFV
        </h1>
        <p className="text-secondary mt-1">
          Drag raw ERP exports and SLA contracts below. The pipeline auto-maps fields,
          extracts penalty clauses, and returns your financial exposure in minutes.
        </p>
      </div>

      {error && (
        <div className="mb-4 flex items-center gap-2 text-critical text-sm p-3 bg-critical/10 rounded-xl border border-critical/30">
          <AlertTriangle size={16} /> {error}
        </div>
      )}

      {/* STEP 1: UPLOAD */}
      {!mappingData && !ingestResult && (
        <div className="step-container glass-panel p-6 mb-4">
          <h2 className="step-title font-bold text-lg mb-4">Step 1: Drop Your Data</h2>
          <div
            className="upload-dropzone"
            onDragOver={e => e.preventDefault()}
            onDrop={handleFileDrop}
          >
            <Upload size={48} className="text-tertiary mb-4" />
            <h3>Drag & Drop SAP/Oracle CSV or Carrier PDF</h3>
            <p>No ETL configuration required.</p>
            <input type="file" onChange={(e) => setFile(e.target.files?.[0] || null)} />

            {file && (
              <div className="selected-file mt-4">
                <FileText size={16} /> <strong>{file.name}</strong>
                <button
                  className="btn-primary mt-4 w-full pulse"
                  onClick={handleAnalyze}
                  disabled={isAnalyzing}
                >
                  {isAnalyzing ? 'AI Scanning & Parsing...' : 'Initiate AI Translation'}
                </button>
              </div>
            )}
          </div>
        </div>
      )}

      {/* STEP 2: AI MAPPING */}
      {mappingData && !ingestResult && (
        <div className="step-container glass-panel p-6 mb-4">
          <div className="mapping-header mb-4">
            <div className="flex justify-between items-center">
              <h2 className="step-title font-bold text-lg">Step 2: Automated AI Translation</h2>
              <span className="badge badge-primary bg-brand-primary text-white px-3 py-1 rounded-full text-xs">
                Domain: {mappingData.detected_domain}
              </span>
            </div>
            <p className="text-sm text-secondary mt-2">
              Fields auto-normalised to Fiscalogix 13-Pillar Schema.
            </p>
          </div>

          {mappingData.raw_headers.length > 0 && (
            <table className="mapping-table w-full mb-6">
              <thead>
                <tr>
                  <th>Raw Customer Header</th>
                  <th>Standardised Token</th>
                </tr>
              </thead>
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

          {/* NLP contract result — real if PDF was uploaded, default otherwise */}
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

      {/* STEP 3: REAL FINANCIAL INSIGHT */}
      {ingestResult && (
        <div
          className="step-container glass-panel p-6 text-center animate-fade-in"
          style={{ border: '1px solid #4ade80', background: 'rgba(74, 222, 128, 0.05)' }}
        >
          <CheckCircle size={64} className="text-safe mx-auto mb-4" />
          <h2 className="text-2xl font-bold mb-2">Step 3: Financial Insight Ready</h2>

          {elapsedSec !== null && (
            <p className="text-xs text-secondary mb-4">
              Total processing time: {elapsedSec}s
            </p>
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
                {ingestResult.financial_impact > 0
                  ? fmtCurrency(ingestResult.financial_impact)
                  : 'Calculating...'}
              </div>
            </div>
          </div>

          <div className="p-4 rounded-xl text-left mb-6" style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid #334155' }}>
            <div className="text-[10px] text-muted uppercase font-bold mb-1">Contract Extract</div>
            <p className="text-sm text-secondary">{ingestResult.nlp_extracted_penalty}</p>
          </div>

          <button className="btn-primary" onClick={() => { onNavigate?.('recovery'); }}>
            Proceed to Recovery Dashboard
          </button>
        </div>
      )}
    </div>
  );
};
