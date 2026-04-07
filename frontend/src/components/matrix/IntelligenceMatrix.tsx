import React, { useState, useEffect, useCallback } from 'react';
import { Filter, Download, MoreVertical, AlertTriangle, ArrowUpDown, ArrowDown, ArrowUp, ChevronLeft, ChevronRight, Loader2 } from 'lucide-react';
import { ConfidencePanel } from './ConfidencePanel';
import { API_BASE_URL } from '../../services/api';
import './IntelligenceMatrix.css';

interface ShipmentRow {
  id: string;
  po_number: string;
  route: string;
  status: string;
  total_value_usd: number;
  expected_efi: number;
  expected_arrival_utc: string | null;
  ml_confidence_score: number;
  ml_risk_detected: boolean;
  // Tech Giant Fields
  robust_revm_floor: number;
  contagion_score_t48: number;
}

export const IntelligenceMatrix: React.FC = () => {
  const [data, setData] = useState<ShipmentRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [totalRecords, setTotalRecords] = useState(0);
  
  const [selectedRows, setSelectedRows] = useState<Set<string>>(new Set());
  const [activeShipmentId, setActiveShipmentId] = useState<string | null>(null);
  const [sortConfig, setSortConfig] = useState<{ key: string, direction: 'asc' | 'desc' }>({ key: 'total_value_usd', direction: 'desc' });

  const fetchGridData = useCallback(async () => {
    setLoading(true);
    try {
      const resp = await fetch(
        `${API_BASE_URL}/datagrid/shipments?page=${page}&limit=50&sort_by=${sortConfig.key}&sort_dir=${sortConfig.direction}`,
        {
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('access_token')}`
          }
        }
      );
      if (resp.ok) {
        const result = await resp.json();
        setData(result.data);
        setTotalPages(result.total_pages);
        setTotalRecords(result.total_records);
      }
    } catch (e) {
      console.error("Failed to fetch grid data", e);
    } finally {
      setLoading(false);
    }
  }, [page, sortConfig]);

  useEffect(() => {
    fetchGridData();
  }, [fetchGridData]);

  const toggleSort = (key: string) => {
    let direction: 'asc' | 'desc' = 'asc';
    if (sortConfig.key === key && sortConfig.direction === 'asc') {
      direction = 'desc';
    }
    setSortConfig({ key, direction });
    setPage(1); // Reset to first page on sort change
  };

  const getSortIcon = (key: string) => {
    if (sortConfig.key === key) {
      return sortConfig.direction === 'asc' ? <ArrowUp size={14} className="ml-1 inline" /> : <ArrowDown size={14} className="ml-1 inline" />;
    }
    return <ArrowUpDown size={14} className="ml-1 inline text-muted" style={{ opacity: 0.3 }} />;
  };

  const exportCSV = () => {
    // In a real app with 1,000,000 rows, this would hit a backend /export endpoint.
    // We'll export the current page for demonstration.
    const headers = ['Shipment ID', 'PO Number', 'Route Line', 'Order Value', 'Margin/Risk Val', 'Risk Score', 'Status'];
    const csvContent = "data:text/csv;charset=utf-8," 
      + headers.join(",") + "\n"
      + data.map(e => `${e.id},${e.po_number},${e.route},${e.total_value_usd},${e.expected_efi},${e.ml_confidence_score},${e.status}`).join("\n");
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", "intelligence_matrix_export.csv");
    document.body.appendChild(link);
    link.click();
    link.remove();
  };

  const toggleRow = (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    const newSelected = new Set(selectedRows);
    if (newSelected.has(id)) newSelected.delete(id);
    else newSelected.add(id);
    setSelectedRows(newSelected);
  };

  const handleRowClick = (id: string) => {
    setActiveShipmentId(id);
  };
  
  // Calculate recommended action based on risk
  const getAction = (risk: number) => {
    if (risk > 0.8) return "REROUTE";
    if (risk > 0.5) return "MONITOR";
    return "NONE";
  };

  return (
    <div className="matrix-container" style={{ position: 'relative', overflow: 'hidden', display: 'flex', flexDirection: 'column', height: '100%' }}>
      <header className="matrix-header shrink-0">
        <div>
          <h1 className="page-title">Intelligence Matrix (Data Grid)</h1>
          <p className="page-subtitle">Server-side Paginated View • {totalRecords.toLocaleString()} Total Records</p>
        </div>
        <div className="header-actions">
          <button className="btn-outline"><Filter size={16} /> Filters</button>
          <button className="btn-outline" onClick={exportCSV}><Download size={16} /> Export CSV</button>
        </div>
      </header>

      <div className="premium-card grid-card flex-grow overflow-hidden flex flex-col">
        {loading ? (
          <div className="flex flex-col items-center justify-center h-full text-secondary">
            <Loader2 size={48} className="animate-spin mb-4 text-brand-primary" />
            <p>Scanning Data Warehouse...</p>
          </div>
        ) : (
          <>
            <div className="table-responsive flex-grow overflow-auto">
              <table className="data-grid w-full">
                <thead className="sticky top-0 bg-surface z-10 shadow-sm">
                  <tr>
                    <th style={{ width: '40px' }}><input type="checkbox" /></th>
                    <th className="sortable-header" onClick={() => toggleSort('po_number')} style={{cursor: 'pointer'}}>PO Number {getSortIcon('po_number')}</th>
                    <th>Route Line</th>
                    <th className="sortable-header" onClick={() => toggleSort('total_value_usd')} style={{cursor: 'pointer'}}>Order Value {getSortIcon('total_value_usd')}</th>
                    <th className="sortable-header" onClick={() => toggleSort('expected_efi')} style={{cursor: 'pointer'}}>Expected EFI {getSortIcon('expected_efi')}</th>
                    <th className="sortable-header" onClick={() => toggleSort('robust_revm_floor')} style={{cursor: 'pointer'}}>Resilience Floor {getSortIcon('robust_revm_floor')}</th>
                    <th className="sortable-header" onClick={() => toggleSort('ml_confidence_score')} style={{cursor: 'pointer'}}>Risk Score {getSortIcon('ml_confidence_score')}</th>
                    <th className="sortable-header" onClick={() => toggleSort('contagion_score_t48')} style={{cursor: 'pointer'}}>Predictive (48h) {getSortIcon('contagion_score_t48')}</th>
                    <th>Recommended Action</th>
                    <th style={{ width: '40px' }}></th>
                  </tr>
                </thead>
                <tbody>
                  {data.length === 0 ? (
                    <tr>
                      <td colSpan={8} className="text-center py-12 text-secondary">
                        No shipments found in Data Warehouse. Go to the Ingestion Studio to upload a CSV.
                      </td>
                    </tr>
                  ) : (
                    data.map((row) => (
                      <tr 
                        key={row.id} 
                        className={activeShipmentId === row.id ? 'selected hover:bg-surface-elevated cursor-pointer' : 'hover:bg-surface-elevated cursor-pointer'}
                        onClick={() => handleRowClick(row.id)}
                      >
                        <td onClick={(e) => toggleRow(row.id, e)}>
                          <input 
                            type="checkbox" 
                            checked={selectedRows.has(row.id)}
                            onChange={() => {}}
                          />
                        </td>
                        <td className="font-medium text-brand-primary">{row.po_number}</td>
                        <td className="text-sm">{row.route}</td>
                        <td className="font-medium">${row.total_value_usd.toLocaleString()}</td>
                        <td className={row.expected_efi < 0 ? 'text-critical' : 'text-safe'}>
                          ${row.expected_efi.toLocaleString()}
                        </td>
                        <td className="text-brand-secondary font-semibold">
                          ${row.robust_revm_floor.toLocaleString()}
                        </td>
                        <td>
                          <div className="risk-badge" data-level={row.ml_confidence_score > 0.8 ? 'high' : row.ml_confidence_score > 0.4 ? 'medium' : 'low'}>
                            {row.ml_confidence_score > 0.8 && <AlertTriangle size={12} />}
                            {(row.ml_confidence_score * 100).toFixed(0)}%
                          </div>
                        </td>
                        <td>
                          <div className="risk-badge" data-level={row.contagion_score_t48 > 0.8 ? 'high' : row.contagion_score_t48 > 0.4 ? 'medium' : 'low'}>
                            {(row.contagion_score_t48 * 100).toFixed(0)}%
                            {row.contagion_score_t48 > row.ml_confidence_score && <ArrowUp size={10} className="ml-0.5" />}
                          </div>
                        </td>
                        <td>
                          <span className={`action-badge action-${getAction(row.ml_confidence_score).toLowerCase()}`}>
                            {getAction(row.ml_confidence_score)}
                          </span>
                        </td>
                        <td>
                          <button className="icon-btn text-secondary hover:text-primary"><MoreVertical size={16} /></button>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>

            {/* Pagination Controls */}
            <div className="flex items-center justify-between px-4 py-3 border-t border-subtle bg-surface shrink-0">
              <div className="text-sm text-secondary">
                Showing <strong>{data.length > 0 ? (page - 1) * 50 + 1 : 0}</strong> to <strong>{Math.min(page * 50, totalRecords)}</strong> of <strong>{totalRecords.toLocaleString()}</strong> results
              </div>
              <div className="flex items-center gap-2">
                <button 
                  className="btn-outline px-2 py-1 flex items-center gap-1"
                  onClick={() => setPage(p => Math.max(1, p - 1))}
                  disabled={page === 1}
                >
                  <ChevronLeft size={16} /> Previous
                </button>
                <span className="text-sm px-3">Page {page} of {totalPages || 1}</span>
                <button 
                  className="btn-outline px-2 py-1 flex items-center gap-1"
                  onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                  disabled={page === totalPages || totalPages === 0}
                >
                  Next <ChevronRight size={16} />
                </button>
              </div>
            </div>
          </>
        )}
      </div>

      <ConfidencePanel 
        shipmentId={activeShipmentId} 
        onClose={() => setActiveShipmentId(null)} 
      />
    </div>
  );
};
