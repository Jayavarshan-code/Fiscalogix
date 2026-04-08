import { useState } from 'react';
import { Shell } from './components/layout/Shell';
import { Dashboard } from './components/dashboard/Dashboard';
import { IntelligenceMatrix } from './components/matrix/IntelligenceMatrix';
import { AuthProvider, useAuth } from './context/AuthContext';
import { Login } from './components/auth/Login';
import { AdminDashboard } from './components/admin/AdminDashboard';
import { IngestionStudio } from './components/ingestion/IngestionStudio';
import ErrorBoundary from './components/layout/ErrorBoundary';
import './App.css';

import { GovernanceDashboardMatrix } from './components/matrix/GovernanceDashboard';
import { CashflowChart } from './components/dashboard/CashflowChart';
import RecoveryDashboard from './components/revenue/RecoveryDashboard';
import { EnterpriseModulesPage } from './components/enterprise/EnterpriseModulesPage';
import { OptimizationPage } from './components/optimization/OptimizationPage';
import { RealtimeHubPage } from './components/realtime/RealtimeHub';

const MainApp = () => {
  const [activeView, setActiveView] = useState<
    'dashboard' | 'matrix' | 'admin' | 'ingest' | 'warehouse' |
    'cashflow' | 'shield' | 'recovery' | 'enterprise' | 'optimization' | 'realtime'
  >('dashboard');
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
            <h2 className="text-2xl font-bold mb-2">Data Warehouse</h2>
            <p className="text-secondary mb-6 text-sm">The 13-Pillar enterprise data lake. All ingested records from ERP systems and CSV uploads are stored and queryable here.</p>
            <div className="glass-panel p-6">
              <h3 className="text-md font-semibold mb-4 text-secondary uppercase tracking-widest text-xs">Recent Ingestion Log</h3>
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-subtle text-muted text-left">
                    <th className="pb-2 pr-4">Table</th>
                    <th className="pb-2 pr-4">Source</th>
                    <th className="pb-2 pr-4">Rows</th>
                    <th className="pb-2">Ingested At</th>
                  </tr>
                </thead>
                <tbody className="text-secondary">
                  <tr className="border-b border-subtle/30">
                    <td className="py-2 pr-4 font-mono text-xs">dw_shipment_facts</td>
                    <td className="py-2 pr-4">BULK-CSV</td>
                    <td className="py-2 pr-4">30,000</td>
                    <td className="py-2 text-muted">Live via Ingestion Studio</td>
                  </tr>
                  <tr className="border-b border-subtle/30">
                    <td className="py-2 pr-4 font-mono text-xs">dw_customer_dimensions</td>
                    <td className="py-2 pr-4">Seeded</td>
                    <td className="py-2 pr-4">500</td>
                    <td className="py-2 text-muted">Setup Seed</td>
                  </tr>
                </tbody>
              </table>
              <p className="text-xs text-muted mt-4">Connect to Postgres via the Ingestion Studio to populate this view with live data.</p>
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
        {activeView === 'enterprise' && <EnterpriseModulesPage />}
        {activeView === 'optimization' && <OptimizationPage />}
        {activeView === 'realtime' && <RealtimeHubPage />}

        {activeView === 'admin' && <AdminDashboard />}
        {activeView === 'shield' && <GovernanceDashboardMatrix />}
      </Shell>
    </div>
  );
};

function App() {
  return (
    <ErrorBoundary>
      <AuthProvider>
        <MainApp />
      </AuthProvider>
    </ErrorBoundary>
  );
}

export default App;
