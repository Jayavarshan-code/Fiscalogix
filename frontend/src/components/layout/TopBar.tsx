import React from 'react';
import { Search, Bell, User } from 'lucide-react';
import './TopBar.css';

export const TopBar: React.FC = () => {

  return (
    <header className="app-topbar">
      <div className="topbar-search">
        <Search size={18} className="search-icon" />
        <input 
          type="text" 
          placeholder="Search shipments, POs, actions..." 
          className="search-input"
        />
      </div>

      <div className="topbar-actions">
        <div className="tenant-selector">
          <span className="tenant-label">Company:</span>
          <select className="tenant-select">
            <option>Acme Corp (Default)</option>
            <option>Globex Sub-Entity</option>
          </select>
        </div>

        <button className="icon-btn alert-btn">
          <Bell size={20} />
          <span className="alert-badge" />
        </button>

        <div className="user-profile">
          <div className="user-avatar">
            <User size={18} />
          </div>
          <span className="user-name">V. Administrator</span>
        </div>
      </div>
    </header>
  );
};
