import React from 'react';
import { TrendingUp, AlertTriangle, Activity, RefreshCw, Gauge } from 'lucide-react';

interface MetricProps {
  label: string;
  value: string;
  trend?: string;
  status: 'safe' | 'warning' | 'critical';
}

const MetricCard: React.FC<MetricProps> = ({ label, value, trend, status }) => (
  <div className="p-4 rounded-2xl bg-surface-elevated border border-subtle shadow-sm flex flex-col gap-1">
    <span className="text-[10px] font-bold text-muted uppercase tracking-widest">{label}</span>
    <div className="flex items-end gap-2">
      <span className={`text-2xl font-black ${status === 'safe' ? 'text-safe' : status === 'warning' ? 'text-warning' : 'text-critical'}`}>
        {value}
      </span>
      {trend && <span className="text-[10px] text-safe font-bold mb-1 mb-1">{trend}</span>}
    </div>
  </div>
);

export const ModelPerformanceDashboard: React.FC = () => {
  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-black text-primary tracking-tighter">AI Governance Hub</h2>
          <p className="text-xs text-muted">Autonomous Feedback & Drift Monitoring</p>
        </div>
        <div className="flex items-center gap-2 px-3 py-1 bg-safe/10 text-safe rounded-full border border-safe/30 animate-pulse">
          <Activity size={14} />
          <span className="text-[10px] font-black uppercase">Live Learning Loop Active</span>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <MetricCard label="Delay Accuracy" value="87.4%" trend="↑ 15.2%" status="safe" />
        <MetricCard label="Cost Accuracy" value="92.1%" trend="↑ 4.8%" status="safe" />
        <MetricCard label="System Bias" value="+₹1,420" status="warning" />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="p-5 rounded-2xl bg-surface-elevated border-l-4 border-l-critical shadow-premium">
          <div className="flex items-center gap-3 mb-4">
            <AlertTriangle className="text-critical" size={20} />
            <h3 className="text-sm font-black uppercase tracking-tight">Active Drift Alert</h3>
          </div>
          <p className="text-xs text-secondary leading-relaxed mb-4">
            Significant **Cost Distribution Shift** detected in the SE-Asia corridor (p=0.0042). 
            System has automatically flagged the base cost model for retraining.
          </p>
          <div className="flex items-center gap-4 py-3 border-t border-subtle">
            <div className="flex flex-col">
              <span className="text-[9px] font-bold text-muted uppercase">Retraining Mode</span>
              <span className="text-[11px] font-black text-brand-primary">Residual Learning (ON)</span>
            </div>
            <div className="flex flex-col">
              <span className="text-[9px] font-bold text-muted uppercase">Last Retrained</span>
              <span className="text-[11px] font-black text-primary">2 Days Ago</span>
            </div>
          </div>
        </div>

        <div className="p-5 rounded-2xl bg-surface-elevated border border-subtle relative overflow-hidden">
          <div className="absolute top-0 right-0 p-4 opacity-10">
            <RefreshCw size={80} className="spin" />
          </div>
          <div className="flex items-center gap-3 mb-4">
            <Gauge className="text-brand-primary" size={20} />
            <h4 className="text-sm font-black uppercase tracking-tight">Learning Insights</h4>
          </div>
          <ul className="space-y-3">
            <li className="flex items-start gap-2">
              <div className="w-1.5 h-1.5 rounded-full bg-safe mt-1.5" />
              <p className="text-[10px] text-secondary">Corrected -12% under-optimism in port storage cost estimates.</p>
            </li>
            <li className="flex items-start gap-2">
              <div className="w-1.5 h-1.5 rounded-full bg-safe mt-1.5" />
              <p className="text-[10px] text-secondary">Improved delay prediction confidence by fusing real-time AIS vessel queues.</p>
            </li>
            <li className="flex items-start gap-2">
              <div className="w-1.5 h-1.5 rounded-full bg-safe mt-1.5" />
              <p className="text-[10px] text-secondary">System trust score increased to <strong>0.94</strong> following weekly epoch.</p>
            </li>
          </ul>
        </div>
      </div>
    </div>
  );
};
