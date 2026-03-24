import React from 'react';
import type { ReactNode } from 'react';
import { Sidebar } from './Sidebar';
import { TopBar } from './TopBar';

interface ShellProps {
  children: ReactNode;
  activeView?: string;
  onNavigate?: (view: string) => void;
}

export const Shell: React.FC<ShellProps> = ({ children, activeView, onNavigate }) => {
  return (
    <div className="app-container">
      <Sidebar activeView={activeView} onNavigate={onNavigate} />
      <TopBar />
      <main className="main-content">
        {children}
      </main>
    </div>
  );
};
