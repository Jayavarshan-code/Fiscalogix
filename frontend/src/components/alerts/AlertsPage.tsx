import React, { useState, useEffect } from 'react';
import {
  Bell, AlertTriangle, CheckCircle, Settings2, Mail,
  MessageSquare, Save, RefreshCw, ShieldAlert, Zap,
} from 'lucide-react';
import { apiService } from '../../services/api';

interface Threshold {
  cash_deficit_usd: number;
  high_risk_shipments: number;
  confidence_floor: number;
}

interface AlertEvent {
  event_type: string;
  severity: 'critical' | 'warning';
  message: string;
  value: number;
  threshold: number;
}

const SEVERITY_COLOR: Record<string, string> = {
  critical: 'var(--semantic-critical, #ef4444)',
  warning:  'var(--semantic-warning, #f59e0b)',
};

const EVENT_ICONS: Record<string, React.ReactNode> = {
  CASH_DEFICIT:      <ShieldAlert size={16} />,
  HIGH_RISK_CLUSTER: <AlertTriangle size={16} />,
  LOW_CONFIDENCE:    <Zap size={16} />,
  SUPPLY_SHOCK:      <AlertTriangle size={16} />,
};

export const AlertsPage: React.FC = () => {
  const [thresholds, setThresholds] = useState<Threshold>({
    cash_deficit_usd:    -10000,
    high_risk_shipments: 3,
    confidence_floor:    0.60,
  });
  const [email, setEmail]       = useState('');
  const [whatsapp, setWhatsapp] = useState('');
  const [saving, setSaving]     = useState(false);
  const [saved, setSaved]       = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  const [checking, setChecking] = useState(false);
  const [alerts, setAlerts]     = useState<AlertEvent[] | null>(null);
  const [checkError, setCheckError] = useState<string | null>(null);

  // Load current thresholds on mount
  useEffect(() => {
    apiService.getAlertThresholds()
      .then((data) => {
        const t = data.thresholds ?? {};
        setThresholds({
          cash_deficit_usd:    t.cash_deficit_usd    ?? -10000,
          high_risk_shipments: t.high_risk_shipments ?? 3,
          confidence_floor:    t.confidence_floor    ?? 0.60,
        });
      })
      .catch(() => { /* use defaults silently */ });
  }, []);

  const handleSave = async () => {
    setSaving(true);
    setSaved(false);
    setSaveError(null);
    try {
      await apiService.configureAlerts({
        ...thresholds,
        alert_email:       email     || undefined,
        alert_whatsapp_to: whatsapp  || undefined,
      });
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch (e: any) {
      setSaveError(e.message || 'Failed to save thresholds.');
    } finally {
      setSaving(false);
    }
  };

  const handleCheck = async () => {
    setChecking(true);
    setAlerts(null);
    setCheckError(null);
    try {
      const result = await apiService.checkAlerts();
      setAlerts(result.alerts ?? []);
    } catch (e: any) {
      setCheckError(e.message || 'Alert check failed.');
    } finally {
      setChecking(false);
    }
  };

  return (
    <div className="p-8 max-w-4xl mx-auto">
      {/* Header */}
      <header style={{ marginBottom: 32 }}>
        <h1 className="page-title" style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <Bell size={24} /> Alerts &amp; Notifications
        </h1>
        <p className="page-subtitle">
          Configure threshold triggers and delivery channels for cash deficits, risk clusters, and supply shocks.
        </p>
      </header>

      {/* Threshold Configuration */}
      <section className="glass-panel" style={{ padding: 28, marginBottom: 24 }}>
        <h2 style={{ fontSize: 15, fontWeight: 700, marginBottom: 20, display: 'flex', alignItems: 'center', gap: 8 }}>
          <Settings2 size={17} /> Alert Thresholds
        </h2>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20 }}>
          {/* Cash Deficit */}
          <div>
            <label style={{ fontSize: 12, color: 'var(--text-secondary)', display: 'block', marginBottom: 6 }}>
              Cash Deficit Floor (USD)
            </label>
            <p style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 8 }}>
              Fire CASH_DEFICIT alert when total ReVM drops below this value.
            </p>
            <input
              type="number"
              value={thresholds.cash_deficit_usd}
              onChange={e => setThresholds(t => ({ ...t, cash_deficit_usd: Number(e.target.value) }))}
              style={inputStyle}
            />
          </div>

          {/* High Risk Shipments */}
          <div>
            <label style={{ fontSize: 12, color: 'var(--text-secondary)', display: 'block', marginBottom: 6 }}>
              High-Risk Shipment Count
            </label>
            <p style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 8 }}>
              Fire HIGH_RISK_CLUSTER when loss shipments reach or exceed this number.
            </p>
            <input
              type="number"
              min={1}
              value={thresholds.high_risk_shipments}
              onChange={e => setThresholds(t => ({ ...t, high_risk_shipments: Number(e.target.value) }))}
              style={inputStyle}
            />
          </div>

          {/* Confidence Floor */}
          <div>
            <label style={{ fontSize: 12, color: 'var(--text-secondary)', display: 'block', marginBottom: 6 }}>
              Confidence Floor (0 – 1)
            </label>
            <p style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 8 }}>
              Fire LOW_CONFIDENCE when system confidence score falls below this value.
            </p>
            <input
              type="number"
              step={0.05}
              min={0}
              max={1}
              value={thresholds.confidence_floor}
              onChange={e => setThresholds(t => ({ ...t, confidence_floor: Number(e.target.value) }))}
              style={inputStyle}
            />
          </div>
        </div>
      </section>

      {/* Delivery Channels */}
      <section className="glass-panel" style={{ padding: 28, marginBottom: 24 }}>
        <h2 style={{ fontSize: 15, fontWeight: 700, marginBottom: 20, display: 'flex', alignItems: 'center', gap: 8 }}>
          Delivery Channels
        </h2>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20 }}>
          {/* Email */}
          <div>
            <label style={{ fontSize: 12, color: 'var(--text-secondary)', display: 'block', marginBottom: 6 }}>
              <Mail size={13} style={{ display: 'inline', marginRight: 5 }} />
              Alert Email (overrides server default)
            </label>
            <input
              type="email"
              placeholder="cfo@yourcompany.com"
              value={email}
              onChange={e => setEmail(e.target.value)}
              style={inputStyle}
            />
            <p style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 6 }}>
              Requires SMTP_HOST configured on the server. Leave blank to use server default.
            </p>
          </div>

          {/* WhatsApp */}
          <div>
            <label style={{ fontSize: 12, color: 'var(--text-secondary)', display: 'block', marginBottom: 6 }}>
              <MessageSquare size={13} style={{ display: 'inline', marginRight: 5 }} />
              WhatsApp Recipient (Twilio)
            </label>
            <input
              type="text"
              placeholder="whatsapp:+919876543210"
              value={whatsapp}
              onChange={e => setWhatsapp(e.target.value)}
              style={inputStyle}
            />
            <p style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 6 }}>
              Format: <code>whatsapp:+[country code][number]</code>. Requires Twilio credentials on server.
            </p>
          </div>
        </div>

        {/* Save button */}
        <div style={{ marginTop: 24, display: 'flex', alignItems: 'center', gap: 12 }}>
          <button
            className="btn-primary"
            onClick={handleSave}
            disabled={saving}
            style={{ display: 'flex', alignItems: 'center', gap: 8 }}
          >
            <Save size={15} />
            {saving ? 'Saving...' : 'Save Configuration'}
          </button>

          {saved && (
            <span style={{ fontSize: 13, color: 'var(--semantic-safe, #4ade80)', display: 'flex', alignItems: 'center', gap: 6 }}>
              <CheckCircle size={15} /> Thresholds saved.
            </span>
          )}
          {saveError && (
            <span style={{ fontSize: 13, color: 'var(--semantic-critical, #ef4444)' }}>
              {saveError}
            </span>
          )}
        </div>
      </section>

      {/* Live Alert Check */}
      <section className="glass-panel" style={{ padding: 28 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
          <h2 style={{ fontSize: 15, fontWeight: 700, display: 'flex', alignItems: 'center', gap: 8 }}>
            <Bell size={17} /> Live Alert Check
          </h2>
          <button
            className="btn-secondary"
            onClick={handleCheck}
            disabled={checking}
            style={{ display: 'flex', alignItems: 'center', gap: 8 }}
          >
            <RefreshCw size={14} className={checking ? 'spin' : ''} />
            {checking ? 'Evaluating...' : 'Run Alert Check Now'}
          </button>
        </div>

        {checkError && (
          <p style={{ color: 'var(--semantic-critical)', fontSize: 13 }}>{checkError}</p>
        )}

        {alerts === null && !checking && (
          <p style={{ fontSize: 13, color: 'var(--text-muted)' }}>
            Click "Run Alert Check Now" to evaluate current financial data against your thresholds.
          </p>
        )}

        {alerts !== null && alerts.length === 0 && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '14px 18px', borderRadius: 8, background: 'rgba(74,222,128,0.08)', border: '1px solid rgba(74,222,128,0.25)' }}>
            <CheckCircle size={18} color="var(--semantic-safe, #4ade80)" />
            <span style={{ fontSize: 13 }}>No alerts — all thresholds are within normal range.</span>
          </div>
        )}

        {alerts !== null && alerts.length > 0 && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <p style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 4 }}>
              {alerts.length} alert{alerts.length > 1 ? 's' : ''} fired
            </p>
            {alerts.map((a, i) => (
              <div
                key={i}
                style={{
                  display: 'flex', alignItems: 'flex-start', gap: 14,
                  padding: '14px 18px', borderRadius: 8,
                  background: a.severity === 'critical' ? 'rgba(239,68,68,0.08)' : 'rgba(245,158,11,0.08)',
                  border: `1px solid ${SEVERITY_COLOR[a.severity]}33`,
                }}
              >
                <span style={{ color: SEVERITY_COLOR[a.severity], marginTop: 2, flexShrink: 0 }}>
                  {EVENT_ICONS[a.event_type] ?? <AlertTriangle size={16} />}
                </span>
                <div style={{ flex: 1 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 4 }}>
                    <strong style={{ fontSize: 13 }}>{a.event_type.replace(/_/g, ' ')}</strong>
                    <span style={{
                      fontSize: 10, fontWeight: 700, padding: '2px 7px', borderRadius: 4,
                      background: SEVERITY_COLOR[a.severity] + '22',
                      color: SEVERITY_COLOR[a.severity],
                      textTransform: 'uppercase',
                    }}>
                      {a.severity}
                    </span>
                  </div>
                  <p style={{ fontSize: 12, color: 'var(--text-secondary)', margin: 0 }}>{a.message}</p>
                  <p style={{ fontSize: 11, color: 'var(--text-muted)', margin: '4px 0 0' }}>
                    Value: {typeof a.value === 'number' ? a.value.toLocaleString() : a.value}
                    {' · '}Threshold: {typeof a.threshold === 'number' ? a.threshold.toLocaleString() : a.threshold}
                  </p>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
};

const inputStyle: React.CSSProperties = {
  width: '100%',
  padding: '9px 12px',
  borderRadius: 6,
  border: '1px solid var(--border-subtle, rgba(255,255,255,0.12))',
  background: 'var(--surface-elevated, rgba(255,255,255,0.04))',
  color: 'inherit',
  fontSize: 14,
  outline: 'none',
};

export default AlertsPage;
