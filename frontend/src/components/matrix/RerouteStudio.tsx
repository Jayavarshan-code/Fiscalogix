import React, { useState } from 'react';
import { X, Ship, Truck, Train, ArrowRight, Info, CheckCircle, Activity, TrendingDown } from 'lucide-react';
import { StochasticScenarioChart } from './StochasticScenarioChart';
import './RerouteStudio.css';

interface RerouteStudioProps {
  shipmentId: string;
  onClose: () => void;
  onConfirm: (mode: string) => void;
}

export const RerouteStudio: React.FC<RerouteStudioProps> = ({ shipmentId, onClose, onConfirm }) => {
  const [selectedMode, setSelectedMode] = useState('RAIL');
  const [holdingCostMultiplier, setHoldingCostMultiplier] = useState(1.0);

  const modes = [
    {
      id: 'TRUCK',
      name: 'Trucking (Current)',
      icon: <Truck size={18} />,
      cost: 5200,
      time: '24h',
      risk: 0.87,
      revm: 11200,
      path: ['Port of Rotterdam', 'Hub A', 'Chicago WH'],
      status: 'CRITICAL SHOCK DETECTED'
    },
    {
      id: 'RAIL',
      name: 'Rail (Stable Alternative)',
      icon: <Train size={18} />,
      cost: 7800,
      time: '72h',
      risk: 0.12,
      revm: 14500,
      path: ['Port of Rotterdam', 'Rail Terminal 4', 'Chicago Intermodal'],
      status: 'OPTIMAL ROBUSTNESS'
    },
    {
      id: 'OCEAN',
      name: 'Ocean (Global Pivot)',
      icon: <Ship size={18} />,
      cost: 3100,
      time: '14 days',
      risk: 0.05,
      revm: 9800,
      path: ['Port of Rotterdam', 'Atlantic Lane 2', 'Port of NY', 'Chicago WH'],
      status: 'CONSERVATIVE BACKUP'
    }
  ];

  const activeMode = modes.find(m => m.id === selectedMode) || modes[0];

  return (
    <div className="reroute-studio-overlay">
      <div className="reroute-studio-content premium-glass">
        <header className="studio-header">
          <div className="flex items-center gap-3">
             <div className="p-2 bg-brand-primary-subtle rounded-lg">
                <Activity size={24} className="text-brand-primary" />
             </div>
             <div>
                <h2>Multimodal Reroute Studio</h2>
                <p className="subtitle">Analyzing Kinetic Alternatives for Shipment {shipmentId}</p>
             </div>
          </div>
          <button className="icon-btn" onClick={onClose}><X size={24} /></button>
        </header>

        <div className="studio-grid">
           {/* Sidebar: Mode Selection */}
           <aside className="mode-sidebar">
              <h3>Select Strategic Mode</h3>
              <div className="mode-list">
                 {modes.map(mode => (
                    <button 
                        key={mode.id}
                        className={`mode-item ${selectedMode === mode.id ? 'active' : ''} ${mode.risk > 0.5 ? 'risk' : ''}`}
                        onClick={() => setSelectedMode(mode.id)}
                    >
                       <div className="mode-icon">{mode.icon}</div>
                       <div className="mode-info">
                          <span className="mode-name">{mode.name}</span>
                          <span className="mode-status">{mode.status}</span>
                       </div>
                    </button>
                 ))}
              </div>

              <div className="simulation-controls mt-8">
                 <div className="flex justify-between items-center mb-2">
                    <span className="text-[10px] font-bold uppercase text-muted">Financial Kinetic Slider</span>
                    <span className="text-[10px] font-bold text-brand-primary">x{holdingCostMultiplier.toFixed(1)}</span>
                 </div>
                 <input 
                    type="range" 
                    min="0.5" 
                    max="3.0" 
                    step="0.1" 
                    value={holdingCostMultiplier}
                    onChange={(e) => setHoldingCostMultiplier(parseFloat(e.target.value))}
                    className="w-full h-1 bg-subtle rounded-lg appearance-none cursor-pointer accent-brand-primary"
                 />
                 <p className="text-[9px] text-secondary mt-2">Adjusting sensitive holding costs (inventory-in-transit) and OTIF contractual penalties.</p>
              </div>
           </aside>

           {/* Main Body: Analysis Panels */}
           <main className="analysis-main">
              <div className="stats-row">
                 <div className="stat-card">
                    <span className="label">Expected ReVM</span>
                    <span className="value">${(activeMode.revm).toLocaleString()}</span>
                    <span className="trend text-safe"><TrendingDown size={12} /> -2% vs Baseline</span>
                 </div>
                 <div className="stat-card">
                    <span className="label">Transit Time</span>
                    <span className="value">{activeMode.time}</span>
                    <span className="trend text-secondary">Velocity Vector</span>
                 </div>
                 <div className="stat-card">
                    <span className="label">Base Cost</span>
                    <span className="value">${activeMode.cost.toLocaleString()}</span>
                    <span className="trend text-muted">Spot Market +5%</span>
                 </div>
              </div>

              <div className="path-analysis mt-6">
                 <h3>Kinetic Path Visualization</h3>
                 <div className="path-stepper">
                    {activeMode.path.map((node, i) => (
                       <React.Fragment key={i}>
                          <div className="path-node">
                             <div className="node-dot"></div>
                             <span className="node-label">{node}</span>
                          </div>
                          {i < activeMode.path.length - 1 && <ArrowRight size={14} className="text-muted" />}
                       </React.Fragment>
                    ))}
                 </div>
              </div>

              <div className="stochastic-deep-dive mt-6">
                 <StochasticScenarioChart 
                    cvarFloor={activeMode.revm - (activeMode.risk * 5000)} 
                    scenarios={Array.from({length: 20}, () => activeMode.revm + (Math.random() - 0.5) * 4000)}
                 />
              </div>

              <div className="studio-actions mt-8">
                 <div className="disclaimer">
                    <Info size={14} />
                    <span>Executing this multimodal pivot will sync with the ERP (SAP/Oracle) and issue immediate Kinetic POE Payloads.</span>
                 </div>
                 <button 
                    className={`btn-execute ${activeMode.risk > 0.5 ? 'critical' : 'safe'}`}
                    onClick={() => onConfirm(activeMode.id)}
                 >
                    <CheckCircle size={18} />
                    Confirm {activeMode.id} Reroute Strategy
                 </button>
              </div>
           </main>
        </div>
      </div>
    </div>
  );
};
