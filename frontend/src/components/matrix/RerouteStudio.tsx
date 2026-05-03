import React, { useState } from 'react';
import { X, Ship, Truck, Train, ArrowRight, Info, CheckCircle, Activity, TrendingDown } from 'lucide-react';
import { StochasticScenarioChart } from './StochasticScenarioChart';
import { FeasibilityScore } from './FeasibilityScore';
import { CostBreakdownTable } from './CostBreakdownTable';

interface RerouteStudioProps {
  shipmentId: string;
  insightsData?: any;   // live data from useShipmentInsights
  onClose: () => void;
  onConfirm: (mode: string) => void;
}

interface ModeOption {
  id: string;
  name: string;
  icon: React.ReactNode;
  cost: number;
  time: string;
  risk: number;
  feasibility: number;
  riskLevel: 'LOW' | 'MEDIUM' | 'HIGH';
  efi: number;
  path: string[];
  status: string;
  breakdown: Record<string, number>;
}

function buildModes(data: any): ModeOption[] {
  // Derive real numbers from live insights; fall back to indicative defaults
  const orderValue  = data?.components?.avg_revenue  ?? 15000;
  const baseCost    = data?.components?.avg_cost      ?? 12750;
  const slaPenalty  = data?.components?.avg_penalty   ?? 0;
  const baseRisk    = Math.max(0.05, 1 - (data?.confidence_score ?? 0.5));

  return [
    {
      id: 'RAIL',
      name: 'Intermodal Rail',
      icon: <Train size={18} />,
      cost: Math.round(baseCost * 1.45),
      time: '72h',
      risk: Math.min(0.99, baseRisk * 0.15),
      feasibility: Math.round(Math.min(99, 82 + (1 - baseRisk) * 15)),
      riskLevel: 'LOW',
      efi: Math.round(orderValue - baseCost * 1.45 - slaPenalty * 0.3),
      path: ['Origin Hub', 'Rail Terminal', 'Destination ICD'],
      status: 'OPTIMAL ROBUSTNESS',
      breakdown: {
        Rail:     Math.round(baseCost * 1.25),
        Handling: Math.round(baseCost * 0.20),
      },
    },
    {
      id: 'TRUCK',
      name: 'Direct Trucking',
      icon: <Truck size={18} />,
      cost: Math.round(baseCost * 0.95),
      time: '24h',
      risk: Math.min(0.99, baseRisk * 0.70),
      feasibility: Math.round(Math.min(99, 50 + (1 - baseRisk) * 18)),
      riskLevel: baseRisk > 0.4 ? 'HIGH' : 'MEDIUM',
      efi: Math.round(orderValue - baseCost * 0.95 - slaPenalty),
      path: ['Origin', 'Direct Route', 'Destination WH'],
      status: baseRisk > 0.4 ? 'CRITICAL SHOCK' : 'VIABLE',
      breakdown: {
        Truck:    Math.round(baseCost * 0.85),
        Handling: Math.round(baseCost * 0.10),
      },
    },
    {
      id: 'OCEAN',
      name: 'Ocean Pivot',
      icon: <Ship size={18} />,
      cost: Math.round(baseCost * 0.35),
      time: '14 days',
      risk: Math.min(0.99, baseRisk * 0.05),
      feasibility: Math.round(Math.min(99, 78 + (1 - baseRisk) * 10)),
      riskLevel: 'MEDIUM',
      efi: Math.round(orderValue - baseCost * 0.35 - slaPenalty * 0.7),
      path: ['Port of Origin', 'Ocean Lane', 'Destination Port', 'Final WH'],
      status: 'CONSERVATIVE',
      breakdown: {
        Ocean:    Math.round(baseCost * 0.25),
        Truck:    Math.round(baseCost * 0.05),
        Handling: Math.round(baseCost * 0.05),
      },
    },
  ];
}

export const RerouteStudio: React.FC<RerouteStudioProps> = ({
  shipmentId,
  insightsData,
  onClose,
  onConfirm,
}) => {
  const [selectedMode, setSelectedMode] = useState('RAIL');
  const [holdingCostMultiplier, setHoldingCostMultiplier] = useState(1.0);

  const modes = buildModes(insightsData);
  const activeMode = modes.find(m => m.id === selectedMode) ?? modes[0];

  const adjustedEfi = Math.round(activeMode.efi * holdingCostMultiplier);

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
           <aside className="mode-sidebar">
              <h3>Select Strategic Mode</h3>
              <div className="mode-list">
                 {modes.map(mode => (
                    <button
                        key={mode.id}
                        className={`mode-item ${selectedMode === mode.id ? 'active' : ''} ${mode.riskLevel === 'HIGH' ? 'risk' : ''}`}
                        onClick={() => setSelectedMode(mode.id)}
                    >
                       <div className="mode-icon">{mode.icon}</div>
                       <div className="mode-info flex-1">
                          <div className="flex justify-between items-center w-full">
                             <span className="mode-name">{mode.name}</span>
                             <span className={`text-[8px] font-black px-1.5 py-0.5 rounded ${mode.riskLevel === 'LOW' ? 'bg-safe/20 text-safe' : 'bg-critical/20 text-critical'}`}>
                                {mode.feasibility}%
                             </span>
                          </div>
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

           <main className="analysis-main">
              <div className="stats-row">
                 <div className="stat-card">
                    <span className="label">Expected EFI</span>
                    <span className="value">₹{adjustedEfi.toLocaleString()}</span>
                    <span className="trend text-safe"><TrendingDown size={12} /> vs Baseline</span>
                 </div>
                 <div className="stat-card">
                    <span className="label">Transit Time</span>
                    <span className="value">{activeMode.time}</span>
                    <span className="trend text-secondary">Velocity Vector</span>
                 </div>
                 <div className="stat-card">
                    <span className="label">Base Cost</span>
                    <span className="value">₹{activeMode.cost.toLocaleString()}</span>
                    <span className="trend text-muted">Live Estimate</span>
                 </div>
              </div>

              <div className="path-analysis mt-6">
                 <div className="flex justify-between items-center mb-3">
                    <h3>Executable Kinetic Path</h3>
                    <FeasibilityScore score={activeMode.feasibility} riskLevel={activeMode.riskLevel} />
                 </div>
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

              <CostBreakdownTable breakdown={activeMode.breakdown as any} total={activeMode.cost} />

              <div className="stochastic-deep-dive mt-6">
                 <StochasticScenarioChart
                    cvarFloor={adjustedEfi - (activeMode.risk * 5000)}
                    scenarios={Array.from({ length: 20 }, () =>
                      adjustedEfi + (Math.random() - 0.5) * 4000
                    )}
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
