import React, { useState } from 'react';
import './VisionDiagnosticModal.tsx.css';

interface VisionResult {
  anomaly_detected: boolean;
  severity: 'low' | 'medium' | 'high';
  description: string;
  financial_impact: string;
}

const VisionDiagnosticModal: React.FC<{ onClose: () => void }> = ({ onClose }) => {
  const [file, setFile] = useState<File | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [result, setResult] = useState<VisionResult | null>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
    }
  };

  const runAnalysis = () => {
    setIsAnalyzing(true);
    // Simulate Vision Agent context processing
    setTimeout(() => {
      setResult({
        anomaly_detected: true,
        severity: 'high',
        description: "Structural puncture detected in center-left quadrant of Container #402. Alignment with packing list suggests internal damage to Tier-1 Optical Sensors.",
        financial_impact: "₹1,45,000 (Loss)"
      });
      setIsAnalyzing(false);
    }, 2000);
  };

  return (
    <div className="vision-modal-overlay">
      <div className="vision-modal-content glass-panel animate-in">
        <div className="modal-header">
          <h3>Pillar 9: Vision Intelligence</h3>
          <button className="close-btn" onClick={onClose}>×</button>
        </div>

        <div className="upload-section">
          {!file ? (
            <label className="drop-zone">
              <span className="upload-icon">📸</span>
              <p>Upload Physical Proof (Damage, Seals, Documents)</p>
              <input type="file" onChange={handleFileChange} hidden />
            </label>
          ) : (
            <div className="file-preview">
              <div className="file-info">
                <span>📎 {file.name}</span>
                <button onClick={() => setFile(null)}>Remove</button>
              </div>
              {!result && !isAnalyzing && (
                <button className="analyze-btn" onClick={runAnalysis}>
                  Run Multi-Modal Diagnostic
                </button>
              )}
            </div>
          )}
        </div>

        {isAnalyzing && (
          <div className="analysis-loading">
            <div className="pulse-ring"></div>
            <p>Correlating Visual Evidence with 13-Pillar Data...</p>
          </div>
        )}

        {result && (
          <div className="vision-result animate-in">
            <div className={`result-badge ${result.severity}`}>
              {result.anomaly_detected ? 'ANOMALY DETECTED' : 'CLEAR'}
            </div>
            <p className="result-desc">{result.description}</p>
            <div className="impact-box">
              <span className="label">ESTIMATED PHYSICAL IMPACT</span>
              <span className="value">{result.financial_impact}</span>
            </div>
            <button className="action-btn">Initialize Insurance Claim</button>
          </div>
        )}
      </div>
    </div>
  );
};

export default VisionDiagnosticModal;
