import React, { useState } from 'react';
import { Loader2, AlertTriangle, CheckCircle, FileText, X } from 'lucide-react';
import { apiService } from '../../services/api';
import './VisionDiagnosticModal.tsx.css';

interface ExtractedDoc {
  doc_id:       string;
  doc_type:     string;
  extracted_fields: Record<string, any>;
  confidence_score: number;
  alerts:       string[];
  anomaly_flags: string[];
  financial_impact_usd?: number;
}

const VisionDiagnosticModal: React.FC<{ onClose: () => void }> = ({ onClose }) => {
  const [file, setFile] = useState<File | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [result, setResult] = useState<ExtractedDoc | null>(null);
  const [error, setError] = useState('');

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files?.[0]) {
      setFile(e.target.files[0]);
      setResult(null);
      setError('');
    }
  };

  const runAnalysis = async () => {
    if (!file) return;
    setIsAnalyzing(true);
    setError('');
    try {
      const doc = await apiService.uploadDocument(file);
      setResult(doc);
    } catch (e: any) {
      setError(e.message || 'Document analysis failed.');
    } finally {
      setIsAnalyzing(false);
    }
  };

  const hasAnomalies = result && (result.anomaly_flags?.length > 0 || result.alerts?.length > 0);
  const severity = hasAnomalies
    ? (result!.anomaly_flags?.length > 1 ? 'high' : 'medium')
    : 'low';

  return (
    <div className="vision-modal-overlay">
      <div className="vision-modal-content glass-panel animate-in">
        <div className="modal-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <h3>Document Intelligence — Vision Pipeline</h3>
          <button className="close-btn" onClick={onClose} style={{ background: 'none', border: 'none', cursor: 'pointer', display: 'flex' }}>
            <X size={18} />
          </button>
        </div>

        <div className="text-[10px] text-muted px-4 mb-2">
          POST /api/v1/documents/upload — OCR → LLM classification → specialist extraction → guardrails
        </div>

        <div className="upload-section">
          {!file ? (
            <label className="drop-zone" style={{ cursor: 'pointer' }}>
              <span className="upload-icon"><FileText size={32} /></span>
              <p>Upload Logistics Document</p>
              <p style={{ fontSize: '10px', color: 'var(--text-muted)' }}>Bill of Lading, Invoice, Contract, Insurance Policy, Damage Report</p>
              <input type="file" onChange={handleFileChange} hidden accept=".pdf,.png,.jpg,.jpeg,.txt,.csv" />
            </label>
          ) : (
            <div className="file-preview">
              <div className="file-info">
                <span>📎 {file.name} ({(file.size / 1024).toFixed(1)} KB)</span>
                <button onClick={() => { setFile(null); setResult(null); setError(''); }}>Remove</button>
              </div>
              {!result && !isAnalyzing && (
                <button className="analyze-btn" onClick={runAnalysis}>
                  Run Multi-Modal Diagnostic Pipeline
                </button>
              )}
            </div>
          )}
        </div>

        {isAnalyzing && (
          <div className="analysis-loading">
            <div className="pulse-ring"></div>
            <p style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Loader2 size={16} className="animate-spin" />
              OCR → Classification → Extraction → Guardrails...
            </p>
          </div>
        )}

        {error && (
          <div style={{ margin: '12px 16px', padding: '10px', background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.3)', borderRadius: '8px', fontSize: '11px', color: 'var(--semantic-critical)', display: 'flex', gap: '8px', alignItems: 'center' }}>
            <AlertTriangle size={14} /> {error}
          </div>
        )}

        {result && (
          <div className="vision-result animate-in">
            <div className={`result-badge ${severity}`}>
              {hasAnomalies ? 'ANOMALY DETECTED' : 'CLEAN EXTRACTION'}
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', margin: '12px 0', fontSize: '10px' }}>
              <div style={{ padding: '8px', background: 'var(--bg-surface)', borderRadius: '8px', border: '1px solid var(--border-subtle)' }}>
                <div style={{ color: 'var(--text-muted)', fontWeight: 'bold', fontSize: '9px', textTransform: 'uppercase', marginBottom: '4px' }}>Doc Type</div>
                <div style={{ color: 'var(--text-primary)', fontWeight: 'bold' }}>{result.doc_type}</div>
              </div>
              <div style={{ padding: '8px', background: 'var(--bg-surface)', borderRadius: '8px', border: '1px solid var(--border-subtle)' }}>
                <div style={{ color: 'var(--text-muted)', fontWeight: 'bold', fontSize: '9px', textTransform: 'uppercase', marginBottom: '4px' }}>Confidence</div>
                <div style={{ color: 'var(--semantic-safe)', fontWeight: 'bold' }}>{((result.confidence_score || 0) * 100).toFixed(1)}%</div>
              </div>
            </div>

            {Object.keys(result.extracted_fields || {}).length > 0 && (
              <div style={{ marginBottom: '10px', padding: '8px', background: 'var(--bg-surface)', borderRadius: '8px', border: '1px solid var(--border-subtle)', fontSize: '10px' }}>
                <div style={{ color: 'var(--text-muted)', fontWeight: 'bold', fontSize: '9px', textTransform: 'uppercase', marginBottom: '6px' }}>Extracted Fields</div>
                {Object.entries(result.extracted_fields).slice(0, 8).map(([k, v]) => (
                  <div key={k} style={{ display: 'flex', justifyContent: 'space-between', padding: '2px 0', borderBottom: '1px solid var(--border-subtle-faint)' }}>
                    <span style={{ color: 'var(--text-secondary)' }}>{k.replace(/_/g, ' ')}</span>
                    <span style={{ color: 'var(--text-primary)', fontWeight: 'bold', fontFamily: 'monospace' }}>{String(v)}</span>
                  </div>
                ))}
              </div>
            )}

            {result.alerts?.length > 0 && (
              <div style={{ marginBottom: '10px' }}>
                <div style={{ color: 'var(--text-muted)', fontWeight: 'bold', fontSize: '9px', textTransform: 'uppercase', marginBottom: '4px' }}>Compliance Alerts</div>
                {result.alerts.map((a, i) => (
                  <div key={i} style={{ display: 'flex', gap: '6px', fontSize: '10px', color: 'var(--semantic-warning)', padding: '4px 0' }}>
                    <AlertTriangle size={12} style={{ flexShrink: 0, marginTop: '1px' }} /> {a}
                  </div>
                ))}
              </div>
            )}

            {result.anomaly_flags?.length > 0 && (
              <div className="impact-box" style={{ background: 'rgba(239,68,68,0.08)', borderColor: 'rgba(239,68,68,0.3)' }}>
                <span className="label">ANOMALIES DETECTED</span>
                {result.anomaly_flags.map((f, i) => (
                  <div key={i} style={{ fontSize: '10px', color: 'var(--semantic-critical)', marginTop: '2px' }}>• {f}</div>
                ))}
              </div>
            )}

            {result.financial_impact_usd != null && (
              <div className="impact-box">
                <span className="label">ESTIMATED FINANCIAL IMPACT</span>
                <span className="value">${Math.abs(result.financial_impact_usd).toLocaleString()} {result.financial_impact_usd < 0 ? '(Loss)' : '(Gain)'}</span>
              </div>
            )}

            {!hasAnomalies && (
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '11px', color: 'var(--semantic-safe)', marginTop: '8px' }}>
                <CheckCircle size={14} /> Document extracted cleanly — no anomalies or compliance flags.
              </div>
            )}

            <button className="action-btn" onClick={() => alert(`Doc ID: ${result.doc_id}\nType: ${result.doc_type}\nStored in document store — available for dispute detection and gap analysis.`)}>
              View in Document Store
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

export default VisionDiagnosticModal;
