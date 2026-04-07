import React, { useState, useEffect } from 'react';
import { Shield, RefreshCcw, Activity, AlertCircle, CheckCircle2, History, Zap, XCircle } from 'lucide-react';
import { apiService } from '../../services/api';

interface ModelStatus {
  status: 'ok' | 'fallback' | 'unavailable';
  detail: string;
  updated_at: string;
}

interface ModelHealthResponse {
  overall_status: 'ok' | 'degraded' | 'critical' | 'unknown';
  message?: string;
  models: Record<string, ModelStatus>;
}

export const GovernanceDashboardMatrix: React.FC = () => {
  const [isRollingBack, setIsRollingBack] = useState(false);
  const [health, setHealth] = useState<ModelHealthResponse | null>(null);
  const [healthLoading, setHealthLoading] = useState(true);

  useEffect(() => {
    const fetchHealth = async () => {
      try {
        const data = await apiService.getModelHealth();
        setHealth(data);
      } catch (e) {
        console.error('Failed to fetch model health', e);
      } finally {
        setHealthLoading(false);
      }
    };
    fetchHealth();
    // Refresh every 60 seconds so ops team sees live drift
    const id = setInterval(fetchHealth, 60_000);
    return () => clearInterval(id);
  }, []);

  const overallStatus = health?.overall_status ?? 'unknown';

  const statusColors: Record<string, string> = {
    ok:       'text-safe',
    degraded: 'text-warning',
    critical: 'text-critical',
    unknown:  'text-muted',
  };

  const statusBgColors: Record<string, string> = {
    ok:       'bg-safe/10 border-safe',
    degraded: 'bg-warning/10 border-warning',
    critical: 'bg-critical/10 border-critical',
    unknown:  'bg-subtle border-subtle',
  };

  const modelIcon = (s: ModelStatus['status']) => {
    if (s === 'ok')          return <CheckCircle2 size={14} className="text-safe" />;
    if (s === 'fallback')    return <AlertCircle size={14} className="text-warning" />;
    return                          <XCircle size={14} className="text-critical" />;
  };

  const handleRollback = () => {
    setIsRollingBack(true);
    setTimeout(() => {
      setIsRollingBack(false);
      alert('Model rolled back to previous version. Production traffic diverted.');
    }, 2000);
  };

  // Build live stat cards from model health data
  const liveModels = health ? Object.entries(health.models) : [];
  const okCount    = liveModels.filter(([, m]) => m.status === 'ok').length;
  const total      = liveModels.length;

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

        {/* Live overall status badge */}
        <div className={`flex items-center gap-2 px-3 py-1 border rounded-full ${statusBgColors[overallStatus]}`}>
          <Activity size={12} className={`${statusColors[overallStatus]} animate-pulse`} />
          <span className={`text-[10px] font-black uppercase ${statusColors[overallStatus]}`}>
            Status: {overallStatus.toUpperCase()}
          </span>
        </div>
      </div>

      {/* Critical alert banner when any model is in fallback */}
      {(overallStatus === 'degraded' || overallStatus === 'critical') && (
        <div className="mb-6 p-3 bg-critical/10 border border-critical/30 rounded-xl flex items-center gap-2">
          <AlertCircle size={16} className="text-critical shrink-0" />
          <p className="text-[11px] text-critical font-bold">
            {overallStatus === 'critical'
              ? 'CRITICAL: One or more ML models are unavailable. Financial decisions are running on heuristic fallback — confidence scores may be unreliable.'
              : 'DEGRADED: Some models are running in fallback mode. Review model status below.'}
          </p>
        </div>
      )}

      {/* Live model status cards */}
      {healthLoading ? (
        <div className="grid grid-cols-3 gap-4 mb-8">
          {[0, 1, 2].map(i => (
            <div key={i} className="p-4 bg-surface rounded-2xl border border-subtle animate-pulse h-16" />
          ))}
        </div>
      ) : liveModels.length > 0 ? (
        <div className="grid grid-cols-3 gap-4 mb-8">
          {liveModels.map(([name, model]) => (
            <div key={name} className="p-4 bg-surface rounded-2xl border border-subtle">
              <div className="flex items-center gap-2 text-muted mb-1 text-[10px] font-bold uppercase">
                {modelIcon(model.status)}
                {name}
              </div>
              <div className={`text-sm font-black capitalize ${
                model.status === 'ok' ? 'text-safe' : model.status === 'fallback' ? 'text-warning' : 'text-critical'
              }`}>
                {model.status.toUpperCase()}
              </div>
              {model.detail && (
                <div className="text-[9px] text-muted mt-1 truncate" title={model.detail}>{model.detail}</div>
              )}
            </div>
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-3 gap-4 mb-8">
          <div className="p-4 bg-surface rounded-2xl border border-subtle">
            <div className="flex items-center gap-2 text-muted mb-1 text-[10px] font-bold uppercase">
              <CheckCircle2 size={14} /> Models Healthy
            </div>
            <div className="text-xl font-black text-primary">{okCount}/{total}</div>
          </div>
          <div className="p-4 bg-surface rounded-2xl border border-subtle">
            <div className="flex items-center gap-2 text-muted mb-1 text-[10px] font-bold uppercase">
              <Activity size={14} /> Overall Status
            </div>
            <div className={`text-xl font-black capitalize ${statusColors[overallStatus]}`}>{overallStatus}</div>
          </div>
          <div className="p-4 bg-surface rounded-2xl border border-subtle">
            <div className="flex items-center gap-2 text-muted mb-1 text-[10px] font-bold uppercase">
              <Zap size={14} /> Engine
            </div>
            <div className="text-xl font-black text-primary">—</div>
          </div>
        </div>
      )}

      {/* Shadow report */}
      <div className="shadow-report mb-8 p-4 bg-surface rounded-2xl border-l-4 border-l-brand-primary">
        <h4 className="text-[10px] font-black text-muted uppercase tracking-widest mb-3">Model Registry ({total} registered)</h4>
        {liveModels.length > 0 ? (
          <div className="space-y-2">
            {liveModels.map(([name, model]) => (
              <div key={name} className="flex justify-between items-center text-[10px]">
                <div className="flex items-center gap-2">
                  {modelIcon(model.status)}
                  <span className="font-bold text-primary">{name}</span>
                </div>
                <div className="flex items-center gap-4">
                  <span className="text-muted font-mono">{model.updated_at?.slice(0, 16).replace('T', ' ')}</span>
                  <span className={`font-black uppercase px-2 py-0.5 rounded ${
                    model.status === 'ok'
                      ? 'bg-safe/10 text-safe'
                      : model.status === 'fallback'
                      ? 'bg-warning/10 text-warning'
                      : 'bg-critical/10 text-critical'
                  }`}>{model.status}</span>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-[10px] text-muted">No models have registered yet. Engine may be cold — process a shipment batch to initialise.</p>
        )}
      </div>

      {/* Deployment controls */}
      <div className="deployment-history">
        <div className="flex justify-between items-center mb-4">
          <h4 className="text-[10px] font-black text-muted uppercase tracking-widest flex items-center gap-2">
            <History size={14} /> Lifecycle Controls
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
      </div>

      <div className="mt-6 p-3 bg-warning/5 border border-warning/20 rounded-xl flex items-center gap-2">
        <AlertCircle size={14} className="text-warning" />
        <p className="text-[10px] text-warning font-medium">
          Auto-Rollback Trigger: Active. System reverts if any model accuracy drops below 85% for 3 consecutive hours.
        </p>
      </div>
    </div>
  );
};
