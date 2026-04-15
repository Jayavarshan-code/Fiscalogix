import React, { useState } from 'react';
import {
  Database, ArrowUp, ArrowDown, ArrowUpDown, ChevronLeft, ChevronRight,
  Download, RefreshCw, AlertTriangle, CheckCircle, Package, TrendingUp,
  Loader2, Search,
} from 'lucide-react';
import { useShipmentGrid } from '../../hooks/queries';
import { useCurrency } from '../../context/CurrencyContext';
import { formatCurrency } from '../../utils/currency';

// ── helpers ───────────────────────────────────────────────────────────────────

const riskLevel = (score: number) =>
  score > 0.75 ? 'HIGH' : score > 0.45 ? 'MEDIUM' : 'LOW';

const riskColor = (score: number) =>
  score > 0.75 ? '#ef4444' : score > 0.45 ? '#f59e0b' : '#4ade80';

const statusColor = (s: string) => {
  switch ((s || '').toUpperCase()) {
    case 'DELIVERED':   return '#4ade80';
    case 'IN_TRANSIT':  return '#60a5fa';
    case 'DELAYED':
    case 'AT_RISK':     return '#f59e0b';
    case 'CRITICAL':    return '#ef4444';
    default:            return '#94a3b8';
  }
};

const fmtDate = (d: string | null) =>
  d ? new Date(d).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: '2-digit' }) : '—';

// ── component ─────────────────────────────────────────────────────────────────

export const ShipmentDataWarehouse: React.FC = () => {
  const [page, setPage]       = useState(1);
  const [sortBy, setSortBy]   = useState('total_value_usd');
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc');
  const [search, setSearch]   = useState('');

  const { currency, fxRate } = useCurrency();

  const { data: gridData, isLoading, refetch, isFetching } = useShipmentGrid(page, sortBy, sortDir);

  const allRows   = gridData?.data          ?? [];
  const totalPages   = gridData?.total_pages   ?? 1;
  const totalRecords = gridData?.total_records ?? 0;

  // client-side search filter (backend doesn't support search param yet)
  const rows = search.trim()
    ? allRows.filter((r: any) =>
        r.po_number?.toLowerCase().includes(search.toLowerCase()) ||
        r.route?.toLowerCase().includes(search.toLowerCase()) ||
        r.status?.toLowerCase().includes(search.toLowerCase())
      )
    : allRows;

  const atRisk      = rows.filter((r: any) => r.ml_risk_detected || r.ml_confidence_score > 0.75).length;
  const totalValue  = rows.reduce((s: number, r: any) => s + (r.total_value_usd ?? 0), 0);
  const avgRisk     = rows.length
    ? rows.reduce((s: number, r: any) => s + (r.ml_confidence_score ?? 0), 0) / rows.length
    : 0;

  const toggleSort = (col: string) => {
    if (sortBy === col) {
      setSortDir(d => d === 'asc' ? 'desc' : 'asc');
    } else {
      setSortBy(col);
      setSortDir('desc');
    }
    setPage(1);
  };

  const SortIcon = ({ col }: { col: string }) =>
    sortBy === col
      ? sortDir === 'asc' ? <ArrowUp size={12} /> : <ArrowDown size={12} />
      : <ArrowUpDown size={12} style={{ opacity: 0.3 }} />;

  const exportCSV = () => {
    const hdr = ['PO Number', 'Route', 'Status', 'Value (USD)', 'Margin (USD)', 'Arrival Date', 'Risk Score', 'Contagion T+48h', 'ReVM Floor'];
    const csv = 'data:text/csv;charset=utf-8,'
      + hdr.join(',') + '\n'
      + rows.map((r: any) =>
          [r.po_number, r.route, r.status, r.total_value_usd, r.margin_usd,
           r.expected_arrival_utc ?? '', r.ml_confidence_score, r.contagion_score_t48, r.robust_revm_floor].join(',')
        ).join('\n');
    const a = document.createElement('a');
    a.href = encodeURI(csv);
    a.download = `dw_shipments_p${page}_${new Date().toISOString().slice(0,10)}.csv`;
    a.click();
  };

  return (
    <div style={{ padding: 32, display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>

      {/* Header */}
      <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 24, flexShrink: 0 }}>
        <div>
          <h1 className="page-title" style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <Database size={22} /> Data Warehouse
          </h1>
          <p className="page-subtitle">
            Live paginated view of <strong>{totalRecords.toLocaleString()}</strong> shipment records from the analytics lake.
          </p>
        </div>
        <div style={{ display: 'flex', gap: 10 }}>
          <button className="btn-secondary" onClick={() => refetch()} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <RefreshCw size={14} className={isFetching ? 'spin' : ''} /> Refresh
          </button>
          <button className="btn-secondary" onClick={exportCSV} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <Download size={14} /> Export CSV
          </button>
        </div>
      </header>

      {/* KPI strip */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 14, marginBottom: 20, flexShrink: 0 }}>
        {[
          { label: 'Total Records',    value: totalRecords.toLocaleString(),                          icon: <Package size={15} />,       color: undefined },
          { label: 'Total Value',      value: formatCurrency(totalValue, currency, fxRate),           icon: <TrendingUp size={15} />,     color: undefined },
          { label: 'At-Risk Shipments',value: `${atRisk} / ${rows.length}`,                           icon: <AlertTriangle size={15} />,  color: atRisk > 0 ? '#ef4444' : '#4ade80' },
          { label: 'Avg Risk Score',   value: `${(avgRisk * 100).toFixed(1)}%`,                       icon: <CheckCircle size={15} />,    color: avgRisk > 0.5 ? '#f59e0b' : '#4ade80' },
        ].map(({ label, value, icon, color }) => (
          <div key={label} style={{
            padding: '12px 16px', borderRadius: 8,
            background: 'rgba(255,255,255,0.03)',
            border: '1px solid rgba(255,255,255,0.08)',
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 11, color: 'var(--text-muted)', marginBottom: 6 }}>
              {icon} {label}
            </div>
            <p style={{ fontSize: 20, fontWeight: 700, margin: 0, color: color ?? 'inherit' }}>{value}</p>
          </div>
        ))}
      </div>

      {/* Search */}
      <div style={{ position: 'relative', marginBottom: 16, flexShrink: 0 }}>
        <Search size={14} style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
        <input
          type="text"
          placeholder="Search PO number, route, or status…"
          value={search}
          onChange={e => setSearch(e.target.value)}
          style={{
            width: '100%', padding: '8px 12px 8px 34px', borderRadius: 6,
            border: '1px solid rgba(255,255,255,0.1)',
            background: 'rgba(255,255,255,0.04)',
            color: 'inherit', fontSize: 13, outline: 'none',
          }}
        />
      </div>

      {/* Table */}
      <div className="glass-panel" style={{ flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column', padding: 0 }}>
        {isLoading ? (
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%', gap: 12 }}>
            <Loader2 size={36} className="animate-spin" style={{ color: 'var(--brand-primary, #6366f1)' }} />
            <p style={{ fontSize: 13, color: 'var(--text-muted)' }}>Scanning Data Warehouse…</p>
          </div>
        ) : (
          <>
            <div style={{ flex: 1, overflowX: 'auto', overflowY: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.1)', position: 'sticky', top: 0, background: 'var(--surface, #0f172a)', zIndex: 5 }}>
                    {[
                      { label: 'PO Number',      col: 'po_number',           w: 130 },
                      { label: 'Route',           col: null,                  w: 180 },
                      { label: 'Status',          col: null,                  w: 110 },
                      { label: `Value`,           col: 'total_value_usd',     w: 120 },
                      { label: 'Margin',          col: 'margin_usd',          w: 110 },
                      { label: 'Expected Arrival',col: null,                  w: 130 },
                      { label: 'Risk Score',      col: 'ml_confidence_score', w: 100 },
                      { label: 'Contagion T+48h', col: 'contagion_score_t48', w: 115 },
                      { label: 'ReVM Floor',      col: 'robust_revm_floor',   w: 110 },
                    ].map(({ label, col, w }) => (
                      <th
                        key={label}
                        onClick={col ? () => toggleSort(col) : undefined}
                        style={{
                          padding: '10px 14px', textAlign: 'left', fontWeight: 600,
                          fontSize: 11, textTransform: 'uppercase', letterSpacing: '0.05em',
                          color: 'var(--text-muted)', cursor: col ? 'pointer' : 'default',
                          width: w, whiteSpace: 'nowrap', userSelect: 'none',
                        }}
                      >
                        <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}>
                          {label}{col && <SortIcon col={col} />}
                        </span>
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {rows.length === 0 ? (
                    <tr>
                      <td colSpan={9} style={{ textAlign: 'center', padding: '48px 0', color: 'var(--text-muted)', fontSize: 13 }}>
                        {totalRecords === 0
                          ? 'No shipments in the warehouse yet. Upload a CSV via the Ingestion Studio.'
                          : 'No shipments match your search.'}
                      </td>
                    </tr>
                  ) : rows.map((row: any) => {
                    const risk = row.ml_confidence_score ?? 0;
                    const rc   = riskColor(risk);
                    const sc   = statusColor(row.status);
                    return (
                      <tr key={row.id} style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}
                        onMouseEnter={e => (e.currentTarget.style.background = 'rgba(255,255,255,0.03)')}
                        onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
                      >
                        <td style={{ padding: '10px 14px', fontWeight: 600, color: 'var(--brand-primary, #6366f1)', fontFamily: 'monospace', fontSize: 12 }}>
                          {row.po_number || '—'}
                        </td>
                        <td style={{ padding: '10px 14px', color: 'var(--text-secondary)', fontSize: 12 }}>{row.route}</td>
                        <td style={{ padding: '10px 14px' }}>
                          <span style={{
                            fontSize: 10, fontWeight: 700, padding: '3px 8px', borderRadius: 4,
                            background: sc + '22', color: sc, border: `1px solid ${sc}44`,
                            textTransform: 'uppercase',
                          }}>
                            {row.status || 'UNKNOWN'}
                          </span>
                        </td>
                        <td style={{ padding: '10px 14px', fontWeight: 600 }}>
                          {formatCurrency(row.total_value_usd ?? 0, currency, fxRate)}
                        </td>
                        <td style={{ padding: '10px 14px', color: (row.margin_usd ?? 0) < 0 ? '#ef4444' : '#4ade80', fontWeight: 600 }}>
                          {formatCurrency(row.margin_usd ?? 0, currency, fxRate)}
                        </td>
                        <td style={{ padding: '10px 14px', color: 'var(--text-secondary)', fontSize: 12 }}>
                          {fmtDate(row.expected_arrival_utc)}
                        </td>
                        <td style={{ padding: '10px 14px' }}>
                          <div style={{ display: 'inline-flex', alignItems: 'center', gap: 5 }}>
                            <div style={{
                              width: 6, height: 6, borderRadius: '50%',
                              background: rc, boxShadow: `0 0 6px ${rc}`,
                              flexShrink: 0,
                            }} />
                            <span style={{ fontSize: 12, fontWeight: 700, color: rc }}>
                              {(risk * 100).toFixed(0)}%
                            </span>
                            <span style={{ fontSize: 10, color: 'var(--text-muted)', marginLeft: 2 }}>
                              {riskLevel(risk)}
                            </span>
                          </div>
                        </td>
                        <td style={{ padding: '10px 14px' }}>
                          <span style={{ fontSize: 12, color: row.contagion_score_t48 > risk ? '#f59e0b' : 'var(--text-secondary)' }}>
                            {(row.contagion_score_t48 * 100).toFixed(0)}%
                            {row.contagion_score_t48 > risk + 0.05 && (
                              <ArrowUp size={10} style={{ display: 'inline', marginLeft: 3, color: '#f59e0b' }} />
                            )}
                          </span>
                        </td>
                        <td style={{ padding: '10px 14px', color: 'var(--text-secondary)', fontSize: 12, fontFamily: 'monospace' }}>
                          {formatCurrency(row.robust_revm_floor ?? 0, currency, fxRate)}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            <div style={{
              display: 'flex', justifyContent: 'space-between', alignItems: 'center',
              padding: '12px 18px', borderTop: '1px solid rgba(255,255,255,0.08)',
              flexShrink: 0, fontSize: 13,
            }}>
              <span style={{ color: 'var(--text-secondary)' }}>
                Showing <strong>{rows.length > 0 ? (page - 1) * 50 + 1 : 0}</strong>–
                <strong>{Math.min(page * 50, totalRecords)}</strong> of{' '}
                <strong>{totalRecords.toLocaleString()}</strong>
              </span>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <button className="btn-secondary"
                  onClick={() => setPage(p => Math.max(1, p - 1))}
                  disabled={page === 1}
                  style={{ display: 'flex', alignItems: 'center', gap: 4, padding: '5px 12px', fontSize: 12 }}>
                  <ChevronLeft size={14} /> Prev
                </button>
                <span style={{ color: 'var(--text-muted)', fontSize: 12 }}>
                  Page {page} / {totalPages || 1}
                </span>
                <button className="btn-secondary"
                  onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                  disabled={page >= totalPages}
                  style={{ display: 'flex', alignItems: 'center', gap: 4, padding: '5px 12px', fontSize: 12 }}>
                  Next <ChevronRight size={14} />
                </button>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
};

export default ShipmentDataWarehouse;
