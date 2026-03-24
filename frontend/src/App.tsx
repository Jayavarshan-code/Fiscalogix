import { useState } from 'react';
import { Shell } from './components/layout/Shell';
import { Dashboard } from './components/dashboard/Dashboard';
import { IntelligenceMatrix } from './components/matrix/IntelligenceMatrix';
import { AuthProvider, useAuth } from './context/AuthContext';
import { Login } from './components/auth/Login';
import { AdminDashboard } from './components/admin/AdminDashboard';
import { IngestionStudio } from './components/ingestion/IngestionStudio';
import './App.css';

const MainApp = () => {
  const [activeView, setActiveView] = useState<'dashboard' | 'matrix' | 'admin' | 'ingest'>('ingest');
  const { currentUser } = useAuth();

  if (!currentUser) {
    return <Login />;
  }

  return (
    <Shell activeView={activeView} onNavigate={(view) => setActiveView(view as 'dashboard' | 'matrix' | 'admin' | 'ingest')}>
      {activeView === 'dashboard' && <Dashboard />}
      {activeView === 'matrix' && <IntelligenceMatrix />}
      {activeView === 'ingest' && <IngestionStudio />}
      {activeView === 'admin' && <AdminDashboard />}
    </Shell>
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
