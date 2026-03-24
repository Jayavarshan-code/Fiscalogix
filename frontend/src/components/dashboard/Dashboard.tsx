import React, { useState } from 'react';
import { KPICard } from './KPICard';
import { DollarSign, AlertTriangle, ShieldCheck, Activity, CheckCircle } from 'lucide-react';
import { CashflowChart } from './CashflowChart';
import { RiskRadar } from './RiskRadar';
import './Dashboard.css';

export const Dashboard: React.FC = () => {
  const [hasShocks, setHasShocks] = useState(true);

  return (
    <div className="dashboard-container">
      <header className="dashboard-header">
        <div>
          <h1 className="page-title">Executive Dashboard</h1>
          <p className="page-subtitle">Real-time systemic risk and locked capital analysis</p>
        </div>
        <div className="header-actions">
          <button className="btn-secondary" onClick={() => setHasShocks(!hasShocks)}>Toggle Shocks: {hasShocks ? 'ON' : 'OFF'}</button>
          <button className="btn-secondary">Export Report</button>
          <button className="btn-primary">Run Global Simulation</button>
        </div>
      </header>

      {/* TOP KPI SECTION - Give me the business in 5 seconds */}
      <section className="kpi-grid">
        <KPICard 
          title="Unlocked Capital" 
          value="$4.2M" 
          trend={12} 
          trendLabel="vs last month"
          icon={<DollarSign size={20} />}
          status="safe"
        />
        <KPICard 
          title="Current REVM" 
          value="$1.15M" 
          trend={-2.4} 
          trendLabel="vs last month"
          icon={<Activity size={20} />}
          status="neutral"
        />
        <KPICard 
          title="Risk Exposure (95% VaR)" 
          value="$845k" 
          trend={5.1} 
          trendLabel="increase in risk"
          icon={<AlertTriangle size={20} />}
          status="warning"
        />
        <KPICard 
          title="System Confidence" 
          value="92%" 
          trend={1.2} 
          trendLabel="data integrity stable"
          icon={<ShieldCheck size={20} />}
          status="safe"
        />
      </section>

      {/* MIDDLE SECTION - Drill down / Visuals */}
      <section className="charts-grid">
        <div className="premium-card chart-card">
          <div className="card-header">
            <h3>Cashflow Trajectory</h3>
            <button className="icon-btn">...</button>
          </div>
          <div className="chart-placeholder">
            <CashflowChart />
          </div>
        </div>

        <div className="premium-card chart-card">
          <div className="card-header">
            <h3>Systemic Shock Radar</h3>
            <button className="icon-btn">...</button>
          </div>
          <div className="chart-placeholder">
            <RiskRadar />
          </div>
        </div>
      </section>

      {/* BOTTOM SECTION - Actionable Alerts */}
      <section className="alerts-section">
        <h3 className="section-title">Systemic Status</h3>
        
        {hasShocks ? (
          <div className="alerts-list">
            <div className="alert-item critical">
              <div className="alert-icon"><AlertTriangle size={16} /></div>
              <div className="alert-content">
                <h4>Projected Cash Deficit (-$45k) in 5 Days</h4>
                <p>Network delays on Route EU-US are extending working capital cycles beyond current liquidity buffers.</p>
              </div>
              <button className="btn-outline">View Mitigation (POE)</button>
            </div>
            <div className="alert-item warning">
              <div className="alert-icon"><AlertTriangle size={16} /></div>
              <div className="alert-content">
                <h4>Elevated Risk Exposure Cluster</h4>
                <p>3 shipments at high risk due to EU port labor strikes. Confidence: 82%.</p>
              </div>
              <button className="btn-outline">Analyze Matrix</button>
            </div>
          </div>
        ) : (
          <div className="premium-card empty-state-card" style={{ textAlign: 'center', padding: '40px' }}>
            <CheckCircle size={48} color="var(--semantic-safe)" style={{ margin: '0 auto 16px' }} />
            <h4 style={{ fontSize: '1.25rem', marginBottom: '8px' }}>All Systems Nominal</h4>
            <p style={{ color: 'var(--text-secondary)' }}>No supply chain shocks or cashflow deficits detected within the 30-day projection window.</p>
          </div>
        )}
      </section>
    </div>
  );
};
