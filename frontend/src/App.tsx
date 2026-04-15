import { useState } from 'react';
import { Shell } from './components/layout/Shell';
import { Dashboard } from './components/dashboard/Dashboard';
import { IntelligenceMatrix } from './components/matrix/IntelligenceMatrix';
import { AuthProvider, useAuth } from './context/AuthContext';
import { Login } from './components/auth/Login';
import { Register } from './components/auth/Register';
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
import { AlertsPage } from './components/alerts/AlertsPage';
import { ReportsPage } from './components/reports/ReportsPage';
import { ShipmentDataWarehouse } from './components/warehouse/ShipmentDataWarehouse';
import { GSTDashboard } from './components/india/GSTDashboard';

const MainApp = () => {
  const [activeView, setActiveView] = useState<
    'dashboard' | 'matrix' | 'admin' | 'ingest' | 'warehouse' |
    'cashflow' | 'shield' | 'recovery' | 'enterprise' | 'optimization' | 'realtime' |
    'alerts' | 'reports' | 'gst'
  >('dashboard');
  const { currentUser } = useAuth();

  const [showRegister, setShowRegister] = useState(false);

  if (!currentUser) {
    return showRegister
      ? <Register onSwitchToLogin={() => setShowRegister(false)} />
      : <Login onSwitchToRegister={() => setShowRegister(true)} />;
  }

  return (
    <div className="flex flex-col min-h-screen">
      <Shell activeView={activeView} onNavigate={(view) => setActiveView(view as any)}>
        {activeView === 'dashboard' && <Dashboard />}
        {activeView === 'matrix' && <IntelligenceMatrix />}
        
        {/* Ingestion Studio — CSV upload and ERP mapping */}
        {activeView === 'ingest' && <IngestionStudio onNavigate={(view) => setActiveView(view as any)} />}

        {/* Data Warehouse — live paginated shipment grid */}
        {activeView === 'warehouse' && <ShipmentDataWarehouse />}
        
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

        {activeView === 'alerts' && <AlertsPage />}
        {activeView === 'reports' && <ReportsPage />}
        {activeView === 'gst' && <GSTDashboard />}

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
