import React from 'react';
import { 
  BarChart3, 
  Activity, 
  Wallet, 
  Zap, 
  Cpu, 
  Settings, 
  Shuffle,
  Shield, // import shield for admin panel
  Database // import database for ingest
} from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import './Sidebar.css';

interface SidebarProps {
  activeView?: string;
  onNavigate?: (view: string) => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ activeView = 'dashboard', onNavigate }) => {
  const { currentUser } = useAuth();

  const handleClick = (e: React.MouseEvent, view: string) => {
    e.preventDefault();
    if (onNavigate) onNavigate(view);
  };

  return (
    <aside className="app-sidebar">
      <div className="sidebar-header">
        <div className="brand-logo">
          <div className="brand-icon" />
          <span className="brand-name">Fiscalogix</span>
        </div>
      </div>

      <nav className="sidebar-nav">
        <div className="nav-group">
          <span className="nav-group-title">Command Center</span>
          <a href="#" className={`nav-item ${activeView === 'dashboard' ? 'active' : ''}`} onClick={(e) => handleClick(e, 'dashboard')}>
            <BarChart3 size={18} />
            Executive Overview
          </a>
          <a href="#" className={`nav-item ${activeView === 'matrix' ? 'active' : ''}`} onClick={(e) => handleClick(e, 'matrix')}>
            <Activity size={18} />
            REVM Analysis
          </a>
          <a href="#" className={`nav-item ${activeView === 'ingest' ? 'active' : ''}`} onClick={(e) => handleClick(e, 'ingest')}>
            <Database size={18} />
            Data Warehouse
          </a>
          <a href="#" className="nav-item">
            <Wallet size={18} />
            Cashflow & Shocks
          </a>
        </div>

        <div className="nav-group">
          <span className="nav-group-title">Intelligence</span>
          <a href="#" className="nav-item">
            <Zap size={18} />
            Optimization (POE)
          </a>
          <a href="#" className="nav-item">
            <Shuffle size={18} />
            Scenario Simulation
          </a>
        </div>

        {currentUser?.profileName === 'System Admin' && (
          <div className="nav-group">
            <span className="nav-group-title">Admin Controls</span>
            <a href="#" className={`nav-item ${activeView === 'admin' ? 'active' : ''}`} onClick={(e) => handleClick(e, 'admin')}>
              <Shield size={18} />
              User Management
            </a>
          </div>
        )}

        <div className="nav-group">
          <span className="nav-group-title">Advanced Control</span>
          <a href="#" className="nav-item">
            <Cpu size={18} />
            Enterprise Modules
          </a>
        </div>
      </nav>

      <div className="sidebar-footer">
        <a href="#" className="nav-item">
          <Settings size={18} />
          Settings
        </a>
      </div>
    </aside>
  );
};
