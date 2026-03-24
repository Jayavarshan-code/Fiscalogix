import React, { useState } from 'react';
import { Upload, FileText, CheckCircle, Database } from 'lucide-react';
import { API_BASE_URL } from '../../services/api';
import './IngestionStudio.css';

interface MappingResult {
  filename: string;
  detected_domain: string;
  raw_headers: string[];
  ai_mapping_suggestions: Record<string, string>;
}

export const IngestionStudio: React.FC = () => {
  const [file, setFile] = useState<File | null>(null);
  const [mappingData, setMappingData] = useState<MappingResult | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [isIngesting, setIsIngesting] = useState(false);
  const [ingestSuccess, setIngestSuccess] = useState<number | null>(null);

  const handleFileDrop = (e: React.DragEvent) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      setFile(e.dataTransfer.files[0]);
      setMappingData(null);
      setIngestSuccess(null);
    }
  };

  const handleAnalyze = async () => {
    if (!file) return;
    setIsAnalyzing(true);
    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await fetch(`${API_BASE_URL}/ingestion/analyze_csv`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${localStorage.getItem('access_token')}` },
        body: formData
      });
      if (response.ok) {
        setMappingData(await response.json());
      }
    } catch (e) {
      console.error(e);
    } finally {
      setIsAnalyzing(false);
    }
  };

  const handleIngest = async () => {
    if (!file) return;
    setIsIngesting(true);
    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await fetch(`${API_BASE_URL}/ingestion/process_csv`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${localStorage.getItem('access_token')}` },
        body: formData // Note: In a real app we'd pass the confirmed mapping dictionary back too
      });
      if (response.ok) {
        const data = await response.json();
        setIngestSuccess(data.rows_ingested);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setIsIngesting(false);
    }
  };

  return (
    <div className="ingestion-studio p-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold flex items-center gap-2"><Database size={24} className="text-brand-primary" /> Universal Data Ingestion</h1>
        <p className="text-secondary mt-1">Upload raw extracts from any system (SAP, Oracle, custom Excel). The AI Mapper will normalize it into the Data Warehouse.</p>
      </div>

      {!mappingData && !ingestSuccess && (
        <div 
          className="upload-dropzone"
          onDragOver={e => e.preventDefault()}
          onDrop={handleFileDrop}
        >
          <Upload size={48} className="text-tertiary mb-4" />
          <h3>Drag and drop CSV Export here</h3>
          <p>or click to browse local files</p>
          <input type="file" accept=".csv" onChange={(e) => setFile(e.target.files?.[0] || null)} />
          
          {file && (
            <div className="selected-file mt-4">
              <FileText size={16} /> <strong>{file.name}</strong>
              <button className="btn-primary mt-4 w-full" onClick={handleAnalyze} disabled={isAnalyzing}>
                {isAnalyzing ? "AI Scanning File..." : "Analyze Schema"}
              </button>
            </div>
          )}
        </div>
      )}

      {mappingData && !ingestSuccess && (
        <div className="mapping-review-card">
          <div className="mapping-header mb-4">
            <div className="flex justify-between items-center">
              <h3 className="font-bold">AI Field Mapping Review</h3>
              <span className="badge badge-primary bg-brand-primary text-white px-3 py-1 rounded-full text-xs">
                Detected Domain: {mappingData.detected_domain}
              </span>
            </div>
            <p className="text-sm text-secondary mt-2">The system recognized these fields. Unmapped columns will be discarded.</p>
          </div>
          
          <table className="mapping-table w-full mb-6">
            <thead>
              <tr>
                <th>Raw Corporate File Header</th>
                <th>Fiscalogix Warehouse Field</th>
                <th>Confidence</th>
              </tr>
            </thead>
            <tbody>
              {mappingData.raw_headers.map((rh, idx) => {
                const target = mappingData.ai_mapping_suggestions[rh];
                return (
                  <tr key={idx}>
                    <td className="font-medium">{rh}</td>
                    <td>
                      {target !== 'UNMAPPED_DISCARD' ? (
                        <span className="badge badge-primary">{target}</span>
                      ) : (
                        <span className="badge badge-outline">Ignored</span>
                      )}
                    </td>
                    <td>
                      {target !== 'UNMAPPED_DISCARD' ? <CheckCircle size={16} className="text-safe" /> : '-'}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>

          <div className="flex justify-end gap-3">
            <button className="btn-outline" onClick={() => setMappingData(null)}>Cancel</button>
            <button className="btn-primary" onClick={handleIngest} disabled={isIngesting}>
              {isIngesting ? "Streaming to Data Warehouse..." : "Confirm & Execute Ingestion"}
            </button>
          </div>
        </div>
      )}

      {ingestSuccess && mappingData && (
        <div className="success-card text-center">
          <CheckCircle size={64} className="text-safe mx-auto mb-4" />
          <h2 className="text-2xl font-bold mb-2">Ingestion Complete</h2>
          <p className="text-secondary mb-6">Successfully streamed <strong>{ingestSuccess.toLocaleString()} rows</strong> into the <code>{mappingData.detected_domain}</code> Analytics Warehouse.</p>
          <button className="btn-primary" onClick={() => { setFile(null); setMappingData(null); setIngestSuccess(null); }}>
            Upload Another Dataset
          </button>
        </div>
      )}
    </div>
  );
};
