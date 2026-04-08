import React, { useState, useEffect } from 'react';
import { AlertTriangle, Activity, RefreshCw, Gauge, Loader2, Database, WifiOff } from 'lucide-react';
import { apiService } from '../../services/api';

interface MLPerformance {
  delay_accuracy_pct: number;
  delay_accuracy_delta: string;
  cost_accuracy_pct: number;
  cost_accuracy_delta: string;
  system_bias_inr: number;
  drift_detected: boolean;
  drift_model: string;
  drift_detail: string;
  retraining_mode: string;
  last_retrained: string;
  trust_score: number;
  learning_insights: string[];
  updated_at: string;
}

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
      {trend && <span className="text-[10px] text-safe font-bold mb-1">{trend}</span>}
    </div>
  </div>
);

export const ModelPerformanceDashboard: React.FC = () => {
  const [perf, setPerf] = useState<MLPerformance | null>(null);
  const [redisStatus, setRedisStatus] = useState<{ available: boolean; host: string; degraded_features: string[]; fallback_behavior: string | null } | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const fetchPerf = async () => {
    setLoading(true); setError('');
    try {
      const [data, redis] = await Promise.all([
        apiService.getMLPerformance(),
        apiService.getRedisStatus().catch(() => null),
      ]);
      setPerf(data);
      setRedisStatus(redis);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchPerf(); }, []);

  if (loading) return (
    <div className="p-6 flex items-center gap-3 text-muted">
      <Loader2 size={20} className="animate-spin" />
      <span className="text-sm">Loading ML performance metrics...</span>
    </div>
  );

  if (error || !perf) return (
    <div className="p-6 text-critical text-sm flex items-center gap-2">
      <AlertTriangle size={16} /> {error || 'Failed to load performance data'}
    </div>
  );

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-black text-primary tracking-tighter">AI Governance Hub</h2>
          <p className="text-xs text-muted">
            Autonomous Feedback & Drift Monitoring ·
            <span className="ml-1 font-mono text-brand-primary">Trust Score: {perf.trust_score}</span>
          </p>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-[9px] text-muted font-mono">
            Updated: {new Date(perf.updated_at).toLocaleTimeString()}
          </span>
          <button onClick={fetchPerf} className="p-1.5 rounded-lg border border-subtle text-muted hover:text-primary transition-colors">
            <RefreshCw size={14} />
          </button>
          <div className="flex items-center gap-2 px-3 py-1 bg-safe/10 text-safe rounded-full border border-safe/30 animate-pulse">
            <Activity size={14} />
            <span className="text-[10px] font-black uppercase">Live Learning Loop Active</span>
          </div>
        </div>
      </div>

      {/* Redis Status Banner */}
      {redisStatus !== null && (
        <div className={`flex items-start gap-3 p-4 rounded-2xl border ${
          redisStatus.available
            ? 'bg-safe/5 border-safe/20'
            : 'bg-critical/5 border-critical/30'
        }`}>
          <div className={`mt-0.5 ${redisStatus.available ? 'text-safe' : 'text-critical'}`}>
            {redisStatus.available ? <Database size={18} /> : <WifiOff size={18} />}
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <span className={`text-[10px] font-black uppercase tracking-widest ${
                redisStatus.available ? 'text-safe' : 'text-critical'
              }`}>
                {redisStatus.available ? 'Redis Cache: Connected' : 'Redis Cache: Offline'}
              </span>
              <span className="text-[9px] font-mono text-muted">{redisStatus.host}</span>
            </div>
            {redisStatus.available ? (
              <p className="text-[10px] text-secondary">WACC overrides, FX volatility cache, and tariff caching are active.</p>
            ) : (
              <>
                <p className="text-[10px] text-secondary mb-2">{redisStatus.fallback_behavior}</p>
                <div className="flex flex-wrap gap-1">
                  {redisStatus.degraded_features.map((f, i) => (
                    <span key={i} className="text-[9px] font-mono px-2 py-0.5 rounded bg-critical/10 text-critical border border-critical/20">
                      {f}
                    </span>
                  ))}
                </div>
              </>
            )}
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <MetricCard
          label="Delay Accuracy"
          value={`${perf.delay_accuracy_pct}%`}
          trend={`↑ ${perf.delay_accuracy_delta}`}
          status="safe"
        />
        <MetricCard
          label="Cost Accuracy"
          value={`${perf.cost_accuracy_pct}%`}
          trend={`↑ ${perf.cost_accuracy_delta}`}
          status="safe"
        />
        <MetricCard
          label="System Bias"
          value={`+₹${perf.system_bias_inr.toLocaleString()}`}
          status={perf.system_bias_inr > 2000 ? 'critical' : 'warning'}
        />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className={`p-5 rounded-2xl bg-surface-elevated shadow-premium border-l-4 ${
          perf.drift_detected ? 'border-l-critical' : 'border-l-safe'
        }`}>
          <div className="flex items-center gap-3 mb-4">
            <AlertTriangle className={perf.drift_detected ? 'text-critical' : 'text-safe'} size={20} />
            <h3 className="text-sm font-black uppercase tracking-tight">
              {perf.drift_detected ? 'Active Drift Alert' : 'No Drift Detected'}
            </h3>
          </div>
          <p className="text-xs text-secondary leading-relaxed mb-4">
            {perf.drift_detail}
          </p>
          <div className="flex items-center gap-4 py-3 border-t border-subtle">
            <div className="flex flex-col">
              <span className="text-[9px] font-bold text-muted uppercase">Retraining Mode</span>
              <span className="text-[11px] font-black text-brand-primary">{perf.retraining_mode}</span>
            </div>
            <div className="flex flex-col">
              <span className="text-[9px] font-bold text-muted uppercase">Last Retrained</span>
              <span className="text-[11px] font-black text-primary">{perf.last_retrained}</span>
            </div>
            {perf.drift_detected && (
              <div className="flex flex-col">
                <span className="text-[9px] font-bold text-muted uppercase">Flagged Model</span>
                <span className="text-[11px] font-black text-critical font-mono">{perf.drift_model}</span>
              </div>
            )}
          </div>
        </div>

        <div className="p-5 rounded-2xl bg-surface-elevated border border-subtle relative overflow-hidden">
          <div className="absolute top-0 right-0 p-4 opacity-10">
            <RefreshCw size={80} className="animate-spin" style={{ animationDuration: '8s' }} />
          </div>
          <div className="flex items-center gap-3 mb-4">
            <Gauge className="text-brand-primary" size={20} />
            <h4 className="text-sm font-black uppercase tracking-tight">Learning Insights</h4>
          </div>
          <ul className="space-y-3">
            {perf.learning_insights.map((insight, i) => (
              <li key={i} className="flex items-start gap-2">
                <div className="w-1.5 h-1.5 rounded-full bg-safe mt-1.5 shrink-0" />
                <p className="text-[10px] text-secondary">{insight}</p>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
};
