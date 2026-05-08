import React, { useEffect, useRef, useState } from 'react';
import {
  BarChart3, Activity, Wallet, Shield, Database, UploadCloud,
  Settings, Briefcase, Layers, Zap, Bell, FileText, ScrollText,
  ChevronDown, Package, Network, TrendingUp,
} from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import './TopMenuRibbon.css';

interface TopMenuRibbonProps {
  activeView?: string;
  onNavigate?: (view: string) => void;
}

const OPT_ITEMS = [
  { view: 'optimization',    label: 'Overview',          badge: '',            icon: Layers     },
  { view: 'opt_delay',       label: 'Delay Prediction',  badge: 'ML',          icon: Zap        },
  { view: 'opt_efi',         label: 'EFI Portfolio',     badge: 'MIP',         icon: BarChart3  },
  { view: 'opt_network',     label: 'Network Router',    badge: 'MILP',        icon: Network    },
  { view: 'opt_montecarlo',  label: 'Monte Carlo',       badge: 'Stochastic',  icon: TrendingUp },
  { view: 'opt_inventory',   label: 'Inventory MEIO',    badge: 'MEIO',        icon: Package    },
];

const isOptimizerView = (v?: string) =>
  v === 'optimization' || (v?.startsWith('opt_') ?? false);

export const TopMenuRibbon: React.FC<TopMenuRibbonProps> = ({ activeView = 'dashboard', onNavigate }) => {
  const { currentUser } = useAuth();
  const [optimizerOpen, setOptimizerOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!optimizerOpen) return;
    const handleClickOutside = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setOptimizerOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [optimizerOpen]);

  const go = (e: React.MouseEvent, view: string) => {
    e.preventDefault();
    if (onNavigate) onNavigate(view);
  };

  const handleOptimizerClick = (e: React.MouseEvent) => {
    e.preventDefault();
    setOptimizerOpen(o => !o);
    // If not already on an optimizer view, navigate to overview
    if (!isOptimizerView(activeView) && onNavigate) onNavigate('optimization');
  };

  return (
    <div className="top-ribbon-container">
      <nav className="tool-ribbon">

        {/* Brand */}
        <div className="ribbon-brand-section">
          <div className="brand-logo-small">
            <div className="brand-icon-small" />
            <span className="brand-name-small">FISCALOGIX</span>
          </div>
        </div>

        <div className="vertical-divider" />

        {/* Executive */}
        <div className="ribbon-group">
          <div className="ribbon-group-title">Executive</div>
          <div className="ribbon-items">
            <a href="#" className={`ribbon-tab ${activeView === 'dashboard' ? 'active' : ''}`} onClick={e => go(e, 'dashboard')}>
              <BarChart3 size={20} /><span>Overview</span>
            </a>
            <a href="#" className={`ribbon-tab ${activeView === 'matrix' ? 'active' : ''}`} onClick={e => go(e, 'matrix')}>
              <Activity size={20} /><span>Matrix</span>
            </a>
            <a href="#" className={`ribbon-tab ${activeView === 'reports' ? 'active' : ''}`} onClick={e => go(e, 'reports')}>
              <FileText size={20} /><span>Reports</span>
            </a>
          </div>
        </div>

        <div className="vertical-divider" />

        {/* Operations */}
        <div className="ribbon-group">
          <div className="ribbon-group-title">Operations</div>
          <div className="ribbon-items">
            <a href="#" className={`ribbon-tab ${activeView === 'ingest' ? 'active' : ''}`} onClick={e => go(e, 'ingest')}>
              <UploadCloud size={20} /><span>Data Link</span>
            </a>
            <a href="#" className={`ribbon-tab ${activeView === 'gst' ? 'active' : ''}`} onClick={e => go(e, 'gst')}>
              <Briefcase size={20} /><span>India GST</span>
            </a>
            <a href="#" className={`ribbon-tab ${activeView === 'warehouse' ? 'active' : ''}`} onClick={e => go(e, 'warehouse')}>
              <Database size={20} /><span>Warehouse</span>
            </a>
            <a href="#" className={`ribbon-tab ${activeView === 'sla' ? 'active' : ''}`} onClick={e => go(e, 'sla')}>
              <ScrollText size={20} /><span>SLA</span>
            </a>
          </div>
        </div>

        <div className="vertical-divider" />

        {/* Intelligence */}
        <div className="ribbon-group">
          <div className="ribbon-group-title">Intelligence</div>
          <div className="ribbon-items">
            <a href="#" className={`ribbon-tab ${activeView === 'recovery' ? 'active' : ''}`} onClick={e => go(e, 'recovery')}>
              <Zap size={20} /><span>Recovery</span>
            </a>
            <a href="#" className={`ribbon-tab ${activeView === 'cashflow' ? 'active' : ''}`} onClick={e => go(e, 'cashflow')}>
              <Wallet size={20} /><span>Cashflow</span>
            </a>

            {/* Optimizer with dropdown */}
            <div className="opt-dropdown-wrapper" ref={dropdownRef}>
              <a
                href="#"
                className={`ribbon-tab opt-dropdown-trigger ${isOptimizerView(activeView) ? 'active' : ''}`}
                onClick={handleOptimizerClick}
              >
                <Layers size={20} />
                <span>Optimizer</span>
                <ChevronDown
                  size={9}
                  className="opt-chevron"
                  style={{ transform: optimizerOpen ? 'rotate(180deg)' : 'rotate(0deg)' }}
                />
              </a>

              {optimizerOpen && (
                <div className="opt-dropdown">
                  <div className="opt-dropdown-header">Optimization Engine</div>
                  {OPT_ITEMS.map(item => (
                    <button
                      key={item.view}
                      className={`opt-dropdown-item ${activeView === item.view ? 'active' : ''}`}
                      onClick={() => {
                        if (onNavigate) onNavigate(item.view);
                        setOptimizerOpen(false);
                      }}
                    >
                      <item.icon size={13} className="opt-item-icon" />
                      <span className="opt-item-label">{item.label}</span>
                      {item.badge && <span className="opt-item-badge">{item.badge}</span>}
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>

        <div className="vertical-divider" />

        {/* System */}
        <div className="ribbon-group">
          <div className="ribbon-group-title">System</div>
          <div className="ribbon-items">
            <a href="#" className={`ribbon-tab ${activeView === 'shield' ? 'active' : ''}`} onClick={e => go(e, 'shield')}>
              <Shield size={20} /><span>Governance</span>
            </a>
            <a href="#" className={`ribbon-tab ${activeView === 'alerts' ? 'active' : ''}`} onClick={e => go(e, 'alerts')}>
              <Bell size={20} /><span>Alerts</span>
            </a>
            <a href="#" className={`ribbon-tab ${activeView === 'admin' ? 'active' : ''}`} onClick={e => go(e, 'admin')}>
              <Settings size={20} /><span>Settings</span>
            </a>
          </div>
        </div>

        {/* User avatar */}
        <div className="ribbon-user-section">
          <div className="avatar-circle">{currentUser?.profileName?.charAt(0) || 'U'}</div>
        </div>

      </nav>
    </div>
  );
};
