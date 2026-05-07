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
import { SLAPage } from './components/sla/SLAPage';

const MainApp = () => {
  const [activeView, setActiveView] = useState<
    'dashboard' | 'matrix' | 'admin' | 'ingest' | 'warehouse' |
    'cashflow' | 'shield' | 'recovery' | 'enterprise' | 'optimization' | 'realtime' |
    'alerts' | 'reports' | 'gst' | 'sla'
  >('dashboard');
  const { currentUser } = useAuth();

  const [showRegister, setShowRegister] = useState(false);

  if (!currentUser) {
    return showRegister
      ? <Register onSwitchToLogin={() => setShowRegister(false)} />
      : <Login onSwitchToRegister={() => setShowRegister(true)} />;
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', minHeight: '100vh', width: '100vw' }}>
      <Shell activeView={activeView} onNavigate={(view) => setActiveView(view as any)}>
        {activeView === 'dashboard' && <Dashboard />}
        {activeView === 'matrix' && <IntelligenceMatrix />}
        
        {/* Ingestion Studio — CSV upload and ERP mapping */}
        {activeView === 'ingest' && <IngestionStudio onNavigate={(view) => setActiveView(view as any)} />}

        {/* Data Warehouse — live paginated shipment grid */}
        {activeView === 'warehouse' && <ShipmentDataWarehouse />}
        
        {activeView === 'cashflow' && (
          <div style={{ padding: '40px 48px 56px 64px', maxWidth: 1000 }}>
            <header style={{ marginBottom: 28, borderBottom: '1px solid rgba(255,255,255,0.08)', paddingBottom: 24 }}>
              <h2 style={{ fontSize: '1.65rem', fontWeight: 700, letterSpacing: '-0.01em', marginBottom: 6 }}>Cashflow &amp; Optimization (POE)</h2>
              <p style={{ fontSize: 13, color: 'var(--text-secondary)' }}>
                90-day AR liquidity trajectory. Click any data point to see what drives that horizon's projection.
              </p>
            </header>
            <div className="glass-panel" style={{ padding: '24px 28px' }}>
              <h3 style={{ fontSize: 13, fontWeight: 700, marginBottom: 20, textTransform: 'uppercase', letterSpacing: '0.06em', opacity: 0.6 }}>Projected Capital Flight</h3>
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

        {activeView === 'sla' && <SLAPage />}
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
