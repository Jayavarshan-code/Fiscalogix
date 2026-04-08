import React from 'react';
import { Loader2, RefreshCw, AlertTriangle } from 'lucide-react';
import { useSpatialRisks } from '../../hooks/queries';
import './SpatialGridOverlay.css';

interface H3Cell {
  id: string;
  event_type: string;
  source_api: string;
  risk_level: 'low' | 'medium' | 'high';
  severity: number;
  status: string;
  detected_at: string | null;
  expires_at: string | null;
}

const EVENT_LABEL: Record<string, string> = {
  PORT_CONGESTION: 'Port Congestion',
  WEATHER:         'Weather',
  GEOPOLITICAL:    'Geopolitical',
};

const SpatialGridOverlay: React.FC = () => {
  const { data, isLoading, isFetching, error, refetch, dataUpdatedAt } = useSpatialRisks();

  const cells: H3Cell[] = data?.cells ?? [];
  const lastUpdated = dataUpdatedAt ? new Date(dataUpdatedAt) : null;

  return (
    <div className="spatial-grid-container glass-panel">
      <div className="grid-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h4>H3 Spatial Risk Matrix</h4>
          <span className="res-tag">Res: 7 · Live</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          {lastUpdated && (
            <span style={{ fontSize: '9px', color: 'var(--text-muted)', fontFamily: 'monospace' }}>
              {lastUpdated.toLocaleTimeString()}
            </span>
          )}
          <button
            onClick={() => refetch()}
            disabled={isFetching}
            style={{ background: 'none', border: '1px solid var(--border-subtle)', borderRadius: '6px', padding: '4px', cursor: 'pointer', display: 'flex', alignItems: 'center', color: 'var(--text-muted)' }}
          >
            <RefreshCw size={12} className={isFetching ? 'animate-spin' : ''} />
          </button>
        </div>
      </div>

      {isLoading ? (
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '24px', color: 'var(--text-muted)', fontSize: '12px' }}>
          <Loader2 size={16} className="animate-spin" /> Loading spatial events...
        </div>
      ) : error ? (
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '12px', color: 'var(--semantic-critical)', fontSize: '11px' }}>
          <AlertTriangle size={14} /> {(error as Error).message}
        </div>
      ) : (
        <div className="hexagon-grid">
          {cells.map((cell) => (
            <div
              key={cell.id}
              className={`hexagon-cell ${cell.risk_level}`}
              title={`${cell.source_api} · Severity: ${(cell.severity * 100).toFixed(0)}%`}
            >
              <div className="hex-content">
                <span className="hex-id" style={{ fontSize: '8px' }}>{cell.id.slice(-8)}</span>
                <span className="hex-status" style={{ fontSize: '8px', fontWeight: 'bold' }}>
                  {EVENT_LABEL[cell.event_type] ?? cell.event_type}
                </span>
                <span style={{ fontSize: '7px', opacity: 0.8 }}>{cell.status.slice(0, 22)}</span>
              </div>
              <div className="hex-top"></div>
              <div className="hex-bottom"></div>
            </div>
          ))}
        </div>
      )}

      <div className="grid-footer">
        <div className="legend-item"><span className="dot red"></span> High Risk</div>
        <div className="legend-item"><span className="dot amber"></span> Medium Risk</div>
        <div className="legend-item"><span className="dot green"></span> Safe</div>
        <span style={{ marginLeft: 'auto', fontSize: '9px', color: 'var(--text-muted)' }}>
          {cells.length} active events
        </span>
      </div>
    </div>
  );
};

export default SpatialGridOverlay;
