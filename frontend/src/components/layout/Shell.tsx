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
    <div className="flex flex-col h-screen" style={{ width: '100vw', margin: 0, padding: 0, overflow: 'hidden', backgroundColor: '#f1f5f9' }}>
      <TopMenuRibbon 
        activeView={activeView} 
        onNavigate={onNavigate} 
      />
      
      {/* Full canvas workspace below the ribbon */}
      <main className="flex-grow w-full relative" style={{ width: '100vw', height: 'calc(100vh - 114px)', margin: 0, padding: 0, boxSizing: 'border-box', overflowY: 'auto' }}>
        {children}
      </main>
    </div>
  );
};
