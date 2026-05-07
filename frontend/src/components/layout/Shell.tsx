import React from 'react';
import type { ReactNode } from 'react';
import { TopMenuRibbon } from './TopMenuRibbon';
import { SyntheticDataBanner } from './SyntheticDataBanner';
import './Shell.css';

interface ShellProps {
  children: ReactNode;
  activeView?: string;
  onNavigate?: (view: string) => void;
}

export const Shell: React.FC<ShellProps> = ({ children, activeView, onNavigate }) => {
  return (
    <div className="shell-root">
      <TopMenuRibbon activeView={activeView} onNavigate={onNavigate} />
      <SyntheticDataBanner />
      <main className="shell-main">
        {children}
      </main>
    </div>
  );
};
