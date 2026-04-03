import { useState } from 'react';
import { Shell } from './components/layout/Shell';
import { Dashboard } from './components/dashboard/Dashboard';
import { IntelligenceMatrix } from './components/matrix/IntelligenceMatrix';
import { AuthProvider, useAuth } from './context/AuthContext';
import { Login } from './components/auth/Login';
import { AdminDashboard } from './components/admin/AdminDashboard';
import { IngestionStudio } from './components/ingestion/IngestionStudio';
import './App.css';

import { GovernanceDashboardMatrix } from './components/matrix/GovernanceDashboard';
import SpatialGridOverlay from './components/matrix/SpatialGridOverlay';
import { CashflowChart } from './components/dashboard/CashflowChart';
import RecoveryDashboard from './components/revenue/RecoveryDashboard';

const MainApp = () => {
  const [activeView, setActiveView] = useState<'dashboard' | 'matrix' | 'admin' | 'ingest' | 'warehouse' | 'cashflow' | 'shield' | 'recovery'>('dashboard');
  const { currentUser } = useAuth();

  if (!currentUser) {
    return <Login />;
  }

  return (
    <div className="flex flex-col min-h-screen">
      <Shell activeView={activeView} onNavigate={(view) => setActiveView(view as any)}>
        {activeView === 'dashboard' && <Dashboard />}
        {activeView === 'matrix' && <IntelligenceMatrix />}
        
        {/* Explicit separation of Ingestion and Warehouse */}
        {activeView === 'ingest' && <IngestionStudio onNavigate={(view) => setActiveView(view as any)} />}
        
        {activeView === 'warehouse' && (
          <div className="p-8">
            <h2 className="text-2xl font-bold mb-4">Data Warehouse (Operational Logs)</h2>
            <div className="glass-panel p-6">
              <p className="text-[var(--text-secondary)] mb-4">Raw 13-Pillar Data Lake</p>
              {/* Rerouting Map visible inside warehouse/logs or matrix */}
              <div style={{ height: '400px', width: '100%', borderRadius: '12px', overflow: 'hidden' }}>
                <SpatialGridOverlay />
              </div>
            </div>
          </div>
        )}
        
        {activeView === 'cashflow' && (
          <div className="p-8">
            <h2 className="text-2xl font-bold mb-4">Cashflow & Optimization (POE)</h2>
            <div className="glass-panel p-6 mb-6">
               <h3 className="text-lg font-bold mb-4">Projected Capital Flight</h3>
               <CashflowChart />
            </div>
          </div>
        )}

        {activeView === 'recovery' && <RecoveryDashboard />}

        {activeView === 'admin' && <AdminDashboard />}
        {activeView === 'shield' && <GovernanceDashboardMatrix />}
      </Shell>
    </div>
  );
};

function App() {
  return (
    <AuthProvider>
      <MainApp />
    </AuthProvider>
  );
}

export default App;
