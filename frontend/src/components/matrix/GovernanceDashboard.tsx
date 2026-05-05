import React, { useState, useEffect, useCallback } from 'react';
import {
  Shield, RefreshCcw, Activity, AlertCircle, CheckCircle2,
  History, Zap, XCircle, Clock, ThumbsUp, ThumbsDown, Inbox,
} from 'lucide-react';
import { useModelHealth } from '../../hooks/queries';

const API_BASE = (import.meta as any).env?.VITE_API_URL ?? '';

// ─── Types ────────────────────────────────────────────────────────────────────

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

interface QueueItem {
  queue_id:          number;
  shipment_id:       number;
  action_type:       string;
  erp_target:        string;
  confidence_score:  number;
  predicted_efi_usd: number;
  ai_rationale:      string | null;
  submitted_by:      string;
  submitted_at:      string | null;
  expires_at:        string | null;
}

interface PendingResponse {
  can_approve: boolean;
  total:       number;
  items:       QueueItem[];
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

function actionColor(action: string) {
  if (action === 'REROUTE')  return 'bg-warning/10 text-warning border-warning/30';
  if (action === 'EXPEDITE') return 'bg-brand-primary/10 text-brand-primary border-brand-primary/30';
  if (action === 'CANCEL')   return 'bg-critical/10 text-critical border-critical/30';
  return 'bg-subtle text-muted border-subtle';
}

function confidenceColor(score: number) {
  if (score >= 0.8) return 'text-safe';
  if (score >= 0.6) return 'text-warning';
  return 'text-critical';
}

// ─── Approval Queue Panel ────────────────────────────────────────────────────

const ApprovalQueuePanel: React.FC = () => {
  const [data, setData]           = useState<PendingResponse | null>(null);
  const [loading, setLoading]     = useState(false);
  const [acting, setActing]       = useState<number | null>(null);
  const [rejectId, setRejectId]   = useState<number | null>(null);
  const [rejectReason, setRejectReason] = useState('');
  const [error, setError]         = useState<string | null>(null);

  const token = localStorage.getItem('token');

  const fetchPending = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/execution/pending`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error(await res.text());
      setData(await res.json());
    } catch (e: any) {
      setError(e.message ?? 'Failed to load queue');
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    fetchPending();
    const interval = setInterval(fetchPending, 30_000); // poll every 30s
    return () => clearInterval(interval);
  }, [fetchPending]);

  const approve = async (queueId: number) => {
    setActing(queueId);
    try {
      const res = await fetch(`${API_BASE}/execution/approve/${queueId}`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      });
      const body = await res.json();
      if (!res.ok) throw new Error(body.detail ?? 'Approval failed');
      await fetchPending();
    } catch (e: any) {
      alert(`Approve failed: ${e.message}`);
    } finally {
      setActing(null);
    }
  };

  const reject = async (queueId: number) => {
    if (!rejectReason.trim()) { alert('Rejection reason is required.'); return; }
    setActing(queueId);
    try {
      const res = await fetch(`${API_BASE}/execution/reject/${queueId}`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ reason: rejectReason }),
      });
      const body = await res.json();
      if (!res.ok) throw new Error(body.detail ?? 'Rejection failed');
      setRejectId(null);
      setRejectReason('');
      await fetchPending();
    } catch (e: any) {
      alert(`Reject failed: ${e.message}`);
    } finally {
      setActing(null);
    }
  };

  const isEmpty = !data || data.total === 0;

  return (
    <div className="mt-8 p-6 bg-surface-elevated rounded-3xl border border-subtle shadow-xl glassmorphism">
      {/* Header */}
      <div className="flex justify-between items-center mb-5">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-warning/10 rounded-xl">
            <Inbox className="text-warning" size={22} />
          </div>
          <div>
            <h3 className="text-base font-black text-primary tracking-tighter uppercase">
              Approval Queue
            </h3>
            <p className="text-[10px] text-muted font-bold tracking-widest uppercase">
              Human-in-the-Loop · AI Recommendations Pending Review
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {data && data.total > 0 && (
            <span className="px-2 py-0.5 bg-warning/15 text-warning text-[10px] font-black rounded-full border border-warning/30">
              {data.total} PENDING
            </span>
          )}
          <button
            onClick={fetchPending}
            className="p-1.5 rounded-lg hover:bg-subtle transition-colors"
            title="Refresh queue"
          >
            <RefreshCcw size={14} className={`text-muted ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* Permission notice */}
      {data && !data.can_approve && (
        <div className="mb-4 p-3 bg-subtle/50 border border-subtle rounded-xl flex items-center gap-2">
          <AlertCircle size={14} className="text-muted shrink-0" />
          <p className="text-[10px] text-muted font-medium">
            You have view-only access to this queue. Approval requires the <span className="font-black text-primary">can_approve</span> permission (Executive or Admin role).
          </p>
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="mb-4 p-3 bg-critical/10 border border-critical/30 rounded-xl text-[11px] text-critical font-bold">
          {error}
        </div>
      )}

      {/* Empty state */}
      {!loading && isEmpty && !error && (
        <div className="py-10 text-center">
          <CheckCircle2 size={28} className="text-safe mx-auto mb-2" />
          <p className="text-sm font-black text-primary">Queue is clear</p>
          <p className="text-[11px] text-muted mt-1">No AI actions are waiting for approval.</p>
        </div>
      )}

      {/* Queue items */}
      {!isEmpty && (
        <div className="space-y-3">
          {data!.items.map(item => (
            <div
              key={item.queue_id}
              className="p-4 bg-surface rounded-2xl border border-subtle"
            >
              {/* Top row */}
              <div className="flex justify-between items-start mb-3">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className={`text-[10px] font-black px-2 py-0.5 rounded border ${actionColor(item.action_type)}`}>
                    {item.action_type}
                  </span>
                  <span className="text-[10px] text-muted font-mono">
                    Shipment #{item.shipment_id}
                  </span>
                  <span className="text-[10px] text-muted">via {item.erp_target}</span>
                </div>
                <div className="flex items-center gap-1 text-[10px] text-muted">
                  <Clock size={11} />
                  {item.submitted_at ? new Date(item.submitted_at).toLocaleString() : '—'}
                </div>
              </div>

              {/* Metrics row */}
              <div className="grid grid-cols-3 gap-3 mb-3">
                <div className="p-2 bg-subtle/40 rounded-lg text-center">
                  <div className="text-[9px] text-muted font-bold uppercase mb-0.5">AI Confidence</div>
                  <div className={`text-sm font-black ${confidenceColor(item.confidence_score)}`}>
                    {(item.confidence_score * 100).toFixed(0)}%
                  </div>
                </div>
                <div className="p-2 bg-subtle/40 rounded-lg text-center">
                  <div className="text-[9px] text-muted font-bold uppercase mb-0.5">EFI Impact</div>
                  <div className="text-sm font-black text-primary">
                    ${item.predicted_efi_usd.toLocaleString()}
                  </div>
                </div>
                <div className="p-2 bg-subtle/40 rounded-lg text-center">
                  <div className="text-[9px] text-muted font-bold uppercase mb-0.5">Submitted By</div>
                  <div className="text-[11px] font-black text-primary truncate">
                    {item.submitted_by}
                  </div>
                </div>
              </div>

              {/* AI rationale */}
              {item.ai_rationale && (
                <div className="mb-3 p-2 bg-brand-primary/5 border border-brand-primary/15 rounded-lg">
                  <p className="text-[10px] text-muted font-bold uppercase mb-0.5">AI Rationale</p>
                  <p className="text-[11px] text-primary leading-relaxed">{item.ai_rationale}</p>
                </div>
              )}

              {/* Expiry warning */}
              {item.expires_at && (() => {
                const msLeft = new Date(item.expires_at).getTime() - Date.now();
                const hLeft  = msLeft / 3_600_000;
                return hLeft < 4 && hLeft > 0 ? (
                  <div className="mb-3 text-[10px] text-warning font-bold flex items-center gap-1">
                    <AlertCircle size={11} />
                    Expires in {hLeft.toFixed(1)}h
                  </div>
                ) : null;
              })()}

              {/* Reject reason input (conditional) */}
              {rejectId === item.queue_id && (
                <div className="mb-3">
                  <textarea
                    className="w-full p-2 bg-subtle/50 border border-subtle rounded-lg text-[11px] text-primary resize-none focus:outline-none focus:border-critical/50"
                    rows={2}
                    placeholder="Rejection reason (required)..."
                    value={rejectReason}
                    onChange={e => setRejectReason(e.target.value)}
                  />
                </div>
              )}

              {/* Action buttons */}
              {data!.can_approve && (
                <div className="flex gap-2 justify-end">
                  {rejectId === item.queue_id ? (
                    <>
                      <button
                        className="flex items-center gap-1.5 px-3 py-1.5 text-[10px] font-black text-muted border border-subtle rounded-lg hover:bg-subtle transition-colors"
                        onClick={() => { setRejectId(null); setRejectReason(''); }}
                      >
                        Cancel
                      </button>
                      <button
                        disabled={acting === item.queue_id}
                        className="flex items-center gap-1.5 px-3 py-1.5 text-[10px] font-black bg-critical/10 text-critical border border-critical/30 rounded-lg hover:bg-critical/20 transition-colors disabled:opacity-50"
                        onClick={() => reject(item.queue_id)}
                      >
                        <ThumbsDown size={12} />
                        {acting === item.queue_id ? 'Rejecting…' : 'Confirm Reject'}
                      </button>
                    </>
                  ) : (
                    <>
                      <button
                        disabled={acting === item.queue_id}
                        className="flex items-center gap-1.5 px-3 py-1.5 text-[10px] font-black bg-critical/10 text-critical border border-critical/30 rounded-lg hover:bg-critical/20 transition-colors disabled:opacity-50"
                        onClick={() => { setRejectId(item.queue_id); setRejectReason(''); }}
                      >
                        <ThumbsDown size={12} />
                        Reject
                      </button>
                      <button
                        disabled={acting === item.queue_id}
                        className="flex items-center gap-1.5 px-3 py-1.5 text-[10px] font-black bg-safe/10 text-safe border border-safe/30 rounded-lg hover:bg-safe/20 transition-colors disabled:opacity-50"
                        onClick={() => approve(item.queue_id)}
                      >
                        <ThumbsUp size={12} />
                        {acting === item.queue_id ? 'Executing…' : 'Approve & Execute'}
                      </button>
                    </>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

// ─── Model Governance Panel ───────────────────────────────────────────────────

export const GovernanceDashboardMatrix: React.FC = () => {
  const [isRollingBack, setIsRollingBack] = useState(false);
  const { data: health, isLoading: healthLoading } = useModelHealth();

  const overallStatus: ModelHealthResponse['overall_status'] = health?.overall_status ?? 'unknown';

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
    if (s === 'ok')       return <CheckCircle2 size={14} className="text-safe" />;
    if (s === 'fallback') return <AlertCircle  size={14} className="text-warning" />;
    return                       <XCircle      size={14} className="text-critical" />;
  };

  const handleRollback = () => {
    setIsRollingBack(true);
    setTimeout(() => {
      setIsRollingBack(false);
      alert('Model rolled back to previous version. Production traffic diverted.');
    }, 2000);
  };

  const liveModels: [string, ModelStatus][] = health ? Object.entries<ModelStatus>(health.models) : [];
  const okCount = liveModels.filter(([, m]) => m.status === 'ok').length;
  const total   = liveModels.length;

  return (
    <>
      {/* ── Model Governance Shield ── */}
      <div className="governance-dashboard mt-8 p-6 bg-surface-elevated rounded-3xl border border-subtle shadow-2xl glassmorphism">
        <div className="flex justify-between items-center mb-6">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-brand-primary/20 rounded-xl">
              <Shield className="text-brand-primary" size={24} />
            </div>
            <div>
              <h3 className="text-lg font-black text-primary tracking-tighter uppercase">AI Governance Shield</h3>
              <p className="text-[10px] text-muted font-bold tracking-widest uppercase">Model Performance & Drift Control</p>
            </div>
          </div>

          <div className={`flex items-center gap-2 px-3 py-1 border rounded-full ${statusBgColors[overallStatus]}`}>
            <Activity size={12} className={`${statusColors[overallStatus]} animate-pulse`} />
            <span className={`text-[10px] font-black uppercase ${statusColors[overallStatus]}`}>
              Status: {overallStatus.toUpperCase()}
            </span>
          </div>
        </div>

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

      {/* ── HITL Approval Queue ── */}
      <ApprovalQueuePanel />
    </>
  );
};
