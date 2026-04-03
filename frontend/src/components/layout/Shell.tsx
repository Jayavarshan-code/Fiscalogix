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
    <div className="flex flex-col min-h-screen" style={{ width: '100vw', margin: 0, padding: 0, overflowX: 'hidden' }}>
      <TopMenuRibbon 
        activeView={activeView} 
        onNavigate={onNavigate} 
      />
      
      <main className="flex-grow w-full p-8" style={{ width: '100vw', margin: 0, boxSizing: 'border-box' }}>
        {children}
      </main>
    </div>
  );
};
