import React from 'react';
import { 
  BarChart3, 
  Activity, 
  Wallet, 
  Shield, 
  Database,
  UploadCloud,
  Settings,
  Briefcase,
  Layers,
  Zap,
  Bell,
  FileText
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
      {/* 1. Native Application Menu Bar (File, Edit, View...) */}
      <div className="application-menu-bar">
        <div className="brand-logo-small">
          <div className="brand-icon-small" />
          <span className="brand-name-small">FISCALOGIX</span>
        </div>
        <div className="menu-items">
          <span className="menu-item hover-menu">File</span>
          <span className="menu-item hover-menu">Edit</span>
          <span className="menu-item hover-menu">View</span>
          <span className="menu-item hover-menu">Workspace</span>
          <span className="menu-item hover-menu">Window</span>
          <span className="menu-item hover-menu">Help</span>
        </div>
        <div className="user-profile-small">
          <div className="avatar-circle">{currentUser?.profileName?.charAt(0) || 'U'}</div>
        </div>
      </div>

      {/* 2. Tool Ribbon (Workspace Navigation) - No permission gating */}
      <nav className="tool-ribbon">
        <div className="ribbon-group">
          <div className="ribbon-group-title">Executive</div>
          <div className="ribbon-items">
            <a href="#" className={`ribbon-tab ${activeView === 'dashboard' ? 'active' : ''}`} onClick={(e) => handleClick(e, 'dashboard')}>
              <BarChart3 size={20} />
              <span>Overview</span>
            </a>
            <a href="#" className={`ribbon-tab ${activeView === 'matrix' ? 'active' : ''}`} onClick={(e) => handleClick(e, 'matrix')}>
              <Activity size={20} />
              <span>Matrix</span>
            </a>
            <a href="#" className={`ribbon-tab ${activeView === 'reports' ? 'active' : ''}`} onClick={(e) => handleClick(e, 'reports')}>
              <FileText size={20} />
              <span>Reports</span>
            </a>
          </div>
        </div>

        <div className="vertical-divider" />

        <div className="ribbon-group">
          <div className="ribbon-group-title">Operations</div>
          <div className="ribbon-items">
            <a href="#" className={`ribbon-tab ${activeView === 'ingest' ? 'active' : ''}`} onClick={(e) => handleClick(e, 'ingest')}>
              <UploadCloud size={20} />
              <span>Data Link</span>
            </a>
            <a href="#" className={`ribbon-tab ${activeView === 'gst' ? 'active' : ''}`} onClick={(e) => handleClick(e, 'gst')}>
              <Briefcase size={20} />
              <span>India GST</span>
            </a>
            <a href="#" className={`ribbon-tab ${activeView === 'warehouse' ? 'active' : ''}`} onClick={(e) => handleClick(e, 'warehouse')}>
              <Database size={20} />
              <span>Warehouse</span>
            </a>
          </div>
        </div>

        <div className="vertical-divider" />

        <div className="ribbon-group">
          <div className="ribbon-group-title">Intelligence</div>
          <div className="ribbon-items">
             <a href="#" className={`ribbon-tab ${activeView === 'recovery' ? 'active' : ''}`} onClick={(e) => handleClick(e, 'recovery')}>
              <Zap size={20} />
              <span>Recovery</span>
            </a>
            <a href="#" className={`ribbon-tab ${activeView === 'cashflow' ? 'active' : ''}`} onClick={(e) => handleClick(e, 'cashflow')}>
              <Wallet size={20} />
              <span>Cashflow</span>
            </a>
             <a href="#" className={`ribbon-tab ${activeView === 'optimization' ? 'active' : ''}`} onClick={(e) => handleClick(e, 'optimization')}>
              <Layers size={20} />
              <span>Optimizer</span>
            </a>
          </div>
        </div>

        <div className="vertical-divider" />

        <div className="ribbon-group">
          <div className="ribbon-group-title">System</div>
          <div className="ribbon-items">
            <a href="#" className={`ribbon-tab ${activeView === 'shield' ? 'active' : ''}`} onClick={(e) => handleClick(e, 'shield')}>
              <Shield size={20} />
              <span>Governance</span>
            </a>
            <a href="#" className={`ribbon-tab ${activeView === 'alerts' ? 'active' : ''}`} onClick={(e) => handleClick(e, 'alerts')}>
              <Bell size={20} />
              <span>Alerts</span>
            </a>
            <a href="#" className={`ribbon-tab ${activeView === 'admin' ? 'active' : ''}`} onClick={(e) => handleClick(e, 'admin')}>
              <Settings size={20} />
              <span>Settings</span>
            </a>
          </div>
        </div>
      </nav>
    </div>
  );
};
