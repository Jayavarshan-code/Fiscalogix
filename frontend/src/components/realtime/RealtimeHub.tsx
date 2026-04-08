import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Activity, Wifi, WifiOff, AlertTriangle, Zap, Radio } from 'lucide-react';
import { API_BASE_URL, apiService } from '../../services/api';

// Convert http(s):// → ws(s)://
const WS_BASE = API_BASE_URL.replace(/^http/, 'ws');

interface RiskEvent {
  type: string;
  data: any;
  ts: number;
}

// ── ERP Field Mapper ──────────────────────────────────────────────────────────
const ERPMappingPanel: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState('');
  const [headerInput, setHeaderInput] = useState('ship_dt, eta_act, cost_inc, val_ord, cust_nm, inv_no');

  const run = async () => {
    setLoading(true); setError(''); setResult(null);
    const headers = headerInput.split(',').map(h => h.trim()).filter(Boolean);
    try { setResult(await apiService.mapERPFields(headers)); }
    catch (e: any) { setError(e.message); }
    finally { setLoading(false); }
  };

  return (
    <div className="glass-panel p-5 rounded-2xl border border-subtle mb-6">
      <h3 className="text-sm font-black text-primary uppercase tracking-tight mb-1">AI ERP Field Mapper</h3>
      <p className="text-[10px] text-muted mb-3">POST /api/v1/mapping/erp — Semantic mapping of raw ERP CSV headers to Financial Twin schema</p>
      <div className="mb-3">
        <label className="text-[9px] font-bold text-muted uppercase block mb-1">ERP CSV Headers (comma-separated)</label>
        <input
          className="w-full bg-surface border border-subtle rounded-lg px-3 py-2 text-xs text-primary font-mono"
          value={headerInput}
          onChange={e => setHeaderInput(e.target.value)}
          placeholder="ship_dt, eta_act, cost_inc..."
        />
      </div>
      <button className="btn-primary text-xs flex items-center gap-2" onClick={run} disabled={loading}>
        {loading
          ? <><span className="animate-spin">⟳</span> Mapping...</>
          : <><Zap size={12} /> Map Fields (AIFieldMapper-v4)</>}
      </button>
      {result && (
        <div className="mt-3">
          <div className="text-[9px] font-bold text-muted uppercase mb-2">
            Mapping Result · Confidence: {(result.confidence * 100).toFixed(0)}% · Engine: {result.engine}
          </div>
          <div className="space-y-1">
            {Object.entries(result.mapping || {}).map(([raw, mapped]: [string, any]) => (
              <div key={raw} className="flex items-center justify-between p-2 bg-surface rounded-lg border border-subtle text-[10px]">
                <span className="font-mono text-warning">{raw}</span>
                <span className="text-muted mx-2">→</span>
                <span className={`font-mono font-bold ${mapped === 'unknown_field' ? 'text-critical' : 'text-safe'}`}>{mapped}</span>
              </div>
            ))}
          </div>
        </div>
      )}
      {error && (
        <div className="mt-3 flex items-center gap-2 text-critical text-[11px] p-3 bg-critical/10 rounded-xl border border-critical/30">
          <AlertTriangle size={14} /> {error}
        </div>
      )}
    </div>
  );
};

// ── WebSocket Risk Hub ────────────────────────────────────────────────────────
const RiskHubPanel: React.FC = () => {
  const [connected, setConnected] = useState(false);
  const [events, setEvents] = useState<RiskEvent[]>([]);
  const [pingMsg, setPingMsg] = useState('');
  const ws = useRef<WebSocket | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  const connect = useCallback(() => {
    if (ws.current?.readyState === WebSocket.OPEN) return;
    try {
      const socket = new WebSocket(`${WS_BASE}/ws/risk-hub`);
      socket.onopen = () => setConnected(true);
      socket.onclose = () => { setConnected(false); ws.current = null; };
      socket.onerror = () => setConnected(false);
      socket.onmessage = (e) => {
        try {
          const data = JSON.parse(e.data);
          setEvents(prev => [{ type: data.type ?? 'MESSAGE', data, ts: Date.now() }, ...prev].slice(0, 50));
        } catch {
          setEvents(prev => [{ type: 'RAW', data: e.data, ts: Date.now() }, ...prev].slice(0, 50));
        }
      };
      ws.current = socket;
    } catch (e) {
      console.error('WebSocket connection failed:', e);
    }
  }, []);

  const disconnect = () => {
    ws.current?.close();
    ws.current = null;
    setConnected(false);
  };

  const sendPing = () => {
    if (ws.current?.readyState === WebSocket.OPEN) {
      const msg = pingMsg || 'ping';
      ws.current.send(msg);
      setEvents(prev => [{ type: 'SENT', data: msg, ts: Date.now() }, ...prev].slice(0, 50));
    }
  };

  useEffect(() => () => ws.current?.close(), []);

  const eventColor = (type: string) => {
    if (type === 'SENT') return 'text-brand-primary';
    if (type === 'RISK_ALERT') return 'text-critical';
    if (type === 'EFI_UPDATE') return 'text-warning';
    return 'text-secondary';
  };

  return (
    <div className="glass-panel p-5 rounded-2xl border border-subtle">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-sm font-black text-primary uppercase tracking-tight flex items-center gap-2">
            <Radio size={14} className={connected ? 'text-safe animate-pulse' : 'text-muted'} />
            Real-Time Risk Hub
          </h3>
          <p className="text-[10px] text-muted mt-0.5">WS /ws/risk-hub — Live risk + EFI stream from backend engine</p>
        </div>
        <div className={`flex items-center gap-1.5 px-3 py-1 rounded-full border text-[9px] font-black uppercase ${
          connected ? 'bg-safe/10 border-safe text-safe' : 'bg-subtle border-subtle text-muted'
        }`}>
          {connected ? <Wifi size={10} /> : <WifiOff size={10} />}
          {connected ? 'Connected' : 'Disconnected'}
        </div>
      </div>

      <div className="flex gap-2 mb-4">
        {!connected
          ? <button className="btn-primary text-xs flex items-center gap-2" onClick={connect}>
              <Activity size={12} /> Connect to Risk Hub
            </button>
          : <button className="btn-outline text-xs flex items-center gap-2 border-critical text-critical" onClick={disconnect}>
              <WifiOff size={12} /> Disconnect
            </button>
        }
        <input
          className="flex-1 bg-surface border border-subtle rounded-lg px-3 py-2 text-xs text-primary"
          placeholder="Send test message..."
          value={pingMsg}
          onChange={e => setPingMsg(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && sendPing()}
          disabled={!connected}
        />
        <button className="btn-outline text-xs" onClick={sendPing} disabled={!connected}>Send</button>
      </div>

      <div ref={scrollRef} className="h-52 overflow-y-auto bg-surface rounded-xl border border-subtle p-3 font-mono text-[10px] space-y-1">
        {events.length === 0 ? (
          <div className="text-muted text-center mt-16">
            {connected ? 'Listening for risk events...' : 'Connect to see live events'}
          </div>
        ) : events.map((e, i) => (
          <div key={i} className="flex gap-2">
            <span className="text-muted shrink-0">{new Date(e.ts).toLocaleTimeString()}</span>
            <span className={`font-bold uppercase shrink-0 ${eventColor(e.type)}`}>[{e.type}]</span>
            <span className="text-secondary truncate">
              {typeof e.data === 'string' ? e.data : JSON.stringify(e.data)}
            </span>
          </div>
        ))}
      </div>

      <div className="mt-3 p-2.5 bg-brand-primary/5 border border-brand-primary/20 rounded-xl text-[10px] text-secondary">
        <strong className="text-brand-primary">How it works:</strong> In production, the backend pushes RISK_ALERT and EFI_UPDATE
        events here when the Pillar 2/5 engines detect anomalies. Connect to see live ACK responses from the hub.
      </div>
    </div>
  );
};

// ── Main Page ─────────────────────────────────────────────────────────────────
export const RealtimeHubPage: React.FC = () => (
  <div className="p-8 max-w-4xl mx-auto">
    <div className="mb-6">
      <h2 className="text-2xl font-black text-primary tracking-tighter">Real-Time & Integration Hub</h2>
      <p className="text-sm text-secondary mt-1">
        Live WebSocket risk stream + AI ERP field mapping.
      </p>
    </div>
    <ERPMappingPanel />
    <RiskHubPanel />
  </div>
);
