import React from 'react';
import { 
  BarChart3, 
  Activity, 
  Wallet, 
  Shield, 
  Database,
  UploadCloud,
  Settings,
  Briefcase
} from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import './TopMenuRibbon.css';

interface TopMenuRibbonProps {
  activeView?: string;
  onNavigate?: (view: string) => void;
}

export const TopMenuRibbon: React.FC<TopMenuRibbonProps> = ({ activeView = 'dashboard', onNavigate }) => {
  const { currentUser } = useAuth();

  const handleClick = (e: React.MouseEvent, view: string) => {
    e.preventDefault();
    if (onNavigate) onNavigate(view);
  };

  return (
    <div className="top-ribbon-container">
      {/* Top Utility Bar (Logo + User) */}
      <div className="ribbon-utility-bar">
        <div className="brand-logo">
          <div className="brand-icon" />
          <span className="brand-name text-lg font-bold ml-2 tracking-wide">FISCALOGIX</span>
        </div>
        <div className="user-profile">
          <span className="text-sm font-semibold mr-4">{currentUser?.profileName}</span>
        </div>
      </div>

      {/* Ribbon Navigation Tabs */}
      <nav className="ribbon-nav">
        <a href="#" className={`ribbon-tab ${activeView === 'dashboard' ? 'active' : ''}`} onClick={(e) => handleClick(e, 'dashboard')}>
          <BarChart3 size={16} />
          <span>Executive Overview</span>
        </a>

        {['Financial Analyst', 'Supply Chain Ops', 'System Admin'].includes(currentUser?.profileName || '') && (
          <a href="#" className={`ribbon-tab ${activeView === 'matrix' ? 'active' : ''}`} onClick={(e) => handleClick(e, 'matrix')}>
            <Activity size={16} />
            <span>REVM Analysis</span>
          </a>
        )}

        <a href="#" className={`ribbon-tab ${activeView === 'ingest' ? 'active' : ''}`} onClick={(e) => handleClick(e, 'ingest')}>
          <UploadCloud size={16} />
          <span>Ingestion Studio</span>
        </a>

        {['System Admin', 'Auditor'].includes(currentUser?.profileName || '') && (
          <a href="#" className={`ribbon-tab ${activeView === 'warehouse' ? 'active' : ''}`} onClick={(e) => handleClick(e, 'warehouse')}>
            <Database size={16} />
            <span>Data Warehouse</span>
          </a>
        )}

        {['Financial Analyst', 'System Admin'].includes(currentUser?.profileName || '') && (
          <a href="#" className={`ribbon-tab ${activeView === 'recovery' ? 'active' : ''}`} onClick={(e) => handleClick(e, 'recovery')}>
            <Briefcase size={16} />
            <span>Revenue Recovery</span>
          </a>
        )}

        {['Executive', 'Financial Analyst', 'System Admin'].includes(currentUser?.profileName || '') && (
          <a href="#" className={`ribbon-tab ${activeView === 'cashflow' ? 'active' : ''}`} onClick={(e) => handleClick(e, 'cashflow')}>
            <Wallet size={16} />
            <span>Cashflow & POE</span>
          </a>
        )}

        {['System Admin', 'Auditor'].includes(currentUser?.profileName || '') && (
          <a href="#" className={`ribbon-tab ${activeView === 'shield' ? 'active' : ''}`} onClick={(e) => handleClick(e, 'shield')}>
            <Shield size={16} />
            <span>AI Governance</span>
          </a>
        )}
        
        {currentUser?.profileName === 'System Admin' && (
          <a href="#" className={`ribbon-tab ${activeView === 'admin' ? 'active' : ''}`} onClick={(e) => handleClick(e, 'admin')}>
            <Settings size={16} />
            <span>Admin & Settings</span>
          </a>
        )}
      </nav>
    </div>
  );
};
