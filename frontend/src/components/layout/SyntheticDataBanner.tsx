import React, { useEffect, useState } from 'react';
import { AlertTriangle, X } from 'lucide-react';

const API_BASE = import.meta.env.VITE_API_URL ?? '';

interface DataQuality {
  shipment_row_count: number;
  is_synthetic: boolean;
  threshold: number;
}

export const SyntheticDataBanner: React.FC = () => {
  const [quality, setQuality] = useState<DataQuality | null>(null);
  const [dismissed, setDismissed] = useState(false);

  useEffect(() => {
    const token = localStorage.getItem('fiscalogix_token');
    if (!token) return;

    fetch(`${API_BASE}/ingestion/data-quality`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => { if (d) setQuality(d); })
      .catch(() => {});
  }, []);

  if (!quality?.is_synthetic || dismissed) return null;

  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: '10px',
        padding: '8px 16px',
        backgroundColor: '#78350f',
        borderBottom: '1px solid #92400e',
        color: '#fef3c7',
        fontSize: '13px',
        flexShrink: 0,
      }}
    >
      <AlertTriangle size={15} style={{ color: '#fbbf24', flexShrink: 0 }} />
      <span>
        <strong style={{ color: '#fcd34d' }}>Synthetic data active</strong>
        {' '}— your tenant has {quality.shipment_row_count.toLocaleString()} shipment
        {quality.shipment_row_count !== 1 ? 's' : ''} (threshold: {quality.threshold.toLocaleString()}).
        ML model predictions are trained on generated data. Upload real shipment data via{' '}
        <strong>Ingestion Studio</strong> to activate live models.
      </span>
      <button
        onClick={() => setDismissed(true)}
        style={{
          marginLeft: 'auto',
          background: 'none',
          border: 'none',
          cursor: 'pointer',
          color: '#fcd34d',
          padding: '2px',
          display: 'flex',
          alignItems: 'center',
        }}
        aria-label="Dismiss banner"
      >
        <X size={14} />
      </button>
    </div>
  );
};
