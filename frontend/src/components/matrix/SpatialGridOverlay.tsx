import React from 'react';
import './SpatialGridOverlay.css';

interface H3Cell {
  id: string;
  risk_level: 'low' | 'medium' | 'high';
  status: string;
}

const SpatialGridOverlay: React.FC = () => {
  const mockCells: H3Cell[] = [
    { id: '87283', risk_level: 'high', status: 'Port Strike Active' },
    { id: '87284', risk_level: 'medium', status: 'Congestion' },
    { id: '87285', risk_level: 'low', status: 'Clear' },
    { id: '87286', risk_level: 'low', status: 'Clear' },
    { id: '87287', risk_level: 'medium', status: 'Heavy Wind' },
    { id: '87288', risk_level: 'high', status: 'Security Breach' },
  ];

  return (
    <div className="spatial-grid-container glass-panel">
      <div className="grid-header">
        <h4>H3 Spatial Risk Matrix</h4>
        <span className="res-tag">Res: 7</span>
      </div>
      <div className="hexagon-grid">
        {mockCells.map((cell) => (
          <div key={cell.id} className={`hexagon-cell ${cell.risk_level}`}>
            <div className="hex-content">
              <span className="hex-id">{cell.id}</span>
              <span className="hex-status">{cell.status}</span>
            </div>
            <div className="hex-top"></div>
            <div className="hex-bottom"></div>
          </div>
        ))}
      </div>
      <div className="grid-footer">
        <div className="legend-item"><span className="dot red"></span> High Risk</div>
        <div className="legend-item"><span className="dot amber"></span> Medium Risk</div>
        <div className="legend-item"><span className="dot green"></span> Safe</div>
      </div>
    </div>
  );
};

export default SpatialGridOverlay;
