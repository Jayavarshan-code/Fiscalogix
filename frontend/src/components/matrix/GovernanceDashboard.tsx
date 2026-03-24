import React, { useState } from 'react';
import { Shield, RefreshCcw, Activity, AlertCircle, CheckCircle2, History, Zap } from 'lucide-react';

export const GovernanceDashboardMatrix: React.FC = () => {
  const [isRollingBack, setIsRollingBack] = useState(false);

  const stats = [
    { label: 'Model Accuracy', value: '94.2%', status: 'stable', icon: <CheckCircle2 size={14} /> },
    { label: 'Drift Score (K-S)', value: '0.041', status: 'stable', icon: <Activity size={14} /> },
    { label: 'Latency (P95)', value: '12ms', status: 'optimal', icon: <Zap size={14} /> },
  ];

  const deploymentLogs = [
    { version: 'v4.2.0', date: '2026-03-24', status: 'ACTIVE', accuracy: '94.2%' },
    { version: 'v4.1.9', date: '2026-03-22', status: 'PREVIOUS', accuracy: '93.8%' },
    { version: 'v4.1.8', date: '2026-03-20', status: 'ARCHIVED', accuracy: '94.0%' },
  ];

  const handleRollback = () => {
    setIsRollingBack(true);
    setTimeout(() => {
      setIsRollingBack(false);
      alert('Model rolled back to v4.1.9. Production traffic diverted.');
    }, 2000);
  };

  return (
    <div className="governance-dashboard mt-8 p-6 bg-surface-elevated rounded-3xl border border-subtle shadow-2xl glassmorphism">
      <div className="flex justify-between items-center mb-6">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-brand-primary/20 rounded-xl">
            <Shield className="text-brand-primary" size={24} />
          </div>
          <div>
            <h3 className="text-lg font-black text-primary tracking-tighter uppercase">AI Governance Shield</h3>
            <p className="text-[10px] text-muted font-bold tracking-widest uppercase">Autonomous Model Lifecycle Control</p>
          </div>
        </div>
        <div className="flex items-center gap-2 px-3 py-1 bg-safe/10 border border-safe rounded-full">
          <Activity size={12} className="text-safe animate-pulse" />
          <span className="text-[10px] font-black text-safe uppercase">Status: HEALTHY</span>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-4 mb-8">
        {stats.map((stat, i) => (
          <div key={i} className="p-4 bg-surface rounded-2xl border border-subtle">
            <div className="flex items-center gap-2 text-muted mb-1 text-[10px] font-bold uppercase">
              {stat.icon}
              {stat.label}
            </div>
            <div className="text-xl font-black text-primary">{stat.value}</div>
          </div>
        ))}
      </div>

      <div className="shadow-report mb-8 p-4 bg-surface rounded-2xl border-l-4 border-l-brand-primary">
         <h4 className="text-[10px] font-black text-muted uppercase tracking-widest mb-3">Model Shadow Report (Candidate vs Prod)</h4>
         <div className="grid grid-cols-2 gap-8">
            <div>
               <span className="text-[9px] font-bold text-muted uppercase block mb-1">Production (v4.2.0)</span>
               <div className="text-sm font-black text-primary">94.2% Acc | 0.88 F1</div>
            </div>
            <div className="border-l border-subtle pl-8">
               <span className="text-[9px] font-bold text-brand-primary uppercase block mb-1">Candidate (v4.3.0-RC)</span>
               <div className="text-sm font-black text-brand-primary">95.1% Acc | 0.91 F1</div>
            </div>
         </div>
      </div>

      <div className="deployment-history">
        <div className="flex justify-between items-center mb-4">
          <h4 className="text-[10px] font-black text-muted uppercase tracking-widest flex items-center gap-2">
            <History size={14} /> Deployment History
          </h4>
          <button 
            className="btn-outline text-[10px] font-black flex items-center gap-2 py-1.5 px-3 border-critical text-critical hover:bg-critical/10"
            onClick={handleRollback}
            disabled={isRollingBack}
          >
            <RefreshCcw size={14} className={isRollingBack ? 'animate-spin' : ''} />
            {isRollingBack ? 'Rolling Back...' : 'Emergency Rollback'}
          </button>
        </div>
        
        <div className="space-y-2">
          {deploymentLogs.map((log, i) => (
            <div key={i} className={`flex justify-between items-center p-3 rounded-xl border border-subtle ${log.status === 'ACTIVE' ? 'bg-brand-primary/10 border-brand-primary/30' : 'bg-surface'}`}>
              <div className="flex items-center gap-3">
                <span className={`text-[10px] font-black px-2 py-0.5 rounded ${log.status === 'ACTIVE' ? 'bg-brand-primary text-white' : 'bg-subtle text-muted'}`}>
                  {log.status}
                </span>
                <span className="text-xs font-bold text-primary">{log.version}</span>
              </div>
              <div className="flex items-center gap-6">
                 <span className="text-[10px] text-muted font-mono">{log.date}</span>
                 <span className="text-xs font-black text-secondary">{log.accuracy} Accuracy</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="mt-6 p-3 bg-warning/5 border border-warning/20 rounded-xl flex items-center gap-2">
         <AlertCircle size={14} className="text-warning" />
         <p className="text-[10px] text-warning font-medium">Auto-Rollback Trigger: Active. Model will revert if accuracy drops below 85% for 3 consecutive hours.</p>
      </div>
    </div>
  );
};
