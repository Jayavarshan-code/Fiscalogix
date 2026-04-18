import React from 'react';
import type { ReactNode } from 'react';
import { TopMenuRibbon } from './TopMenuRibbon';

interface ShellProps {
  children: ReactNode;
  activeView?: string;
  onNavigate?: (view: string) => void;
}

export const Shell: React.FC<ShellProps> = ({ children, activeView, onNavigate }) => {

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', width: '100vw', margin: 0, padding: 0, overflow: 'hidden', backgroundColor: '#e2e8f0' }}>
      <TopMenuRibbon 
        activeView={activeView} 
        onNavigate={onNavigate} 
      />
      
      {/* Full canvas workspace below the ribbon */}
      <main style={{ flexGrow: 1, width: '100vw', height: 'calc(100vh - 82px)', margin: 0, padding: 0, boxSizing: 'border-box', overflowY: 'auto' }}>
        {children}
      </main>
    </div>
  );
};
