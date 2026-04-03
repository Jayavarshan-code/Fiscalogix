import { Component } from 'react';
import type { ErrorInfo, ReactNode } from 'react';


interface Props {
  children: ReactNode;
  fallbackMessage?: string;
}

interface State {
  hasError: boolean;
  errorMessage: string;
}

/**
 * Global Error Boundary.
 * Catches any runtime exceptions thrown by child React components and renders
 * a graceful error screen instead of a white/blank page crash.
 */
class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    errorMessage: ''
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, errorMessage: error.message };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    // In production, send this to an error tracking service like Sentry
    console.error('Fiscalogix Error Boundary Caught:', error, errorInfo);
  }

  public render() {
    if (this.state.hasError) {
      return (
        <div style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          height: '100vh',
          background: 'var(--bg-primary, #0f172a)',
          color: 'var(--text-primary, #e2e8f0)',
          fontFamily: 'Inter, sans-serif',
          gap: '16px',
          padding: '32px'
        }}>
          <div style={{ fontSize: '48px' }}>⚠️</div>
          <h2 style={{ fontSize: '22px', fontWeight: 700, margin: 0 }}>
            {this.props.fallbackMessage || 'An unexpected error occurred'}
          </h2>
          <p style={{ color: '#94a3b8', fontSize: '14px', maxWidth: '480px', textAlign: 'center' }}>
            The Fiscalogix engine encountered a problem loading this view. Please refresh the page. If the issue persists, check the backend connection.
          </p>
          <code style={{
            background: '#1e293b',
            padding: '12px 16px',
            borderRadius: '8px',
            fontSize: '12px',
            color: '#f87171',
            maxWidth: '600px',
            wordBreak: 'break-all'
          }}>
            {this.state.errorMessage}
          </code>
          <button
            onClick={() => window.location.reload()}
            style={{
              marginTop: '8px',
              padding: '10px 24px',
              background: '#2563eb',
              color: '#fff',
              border: 'none',
              borderRadius: '8px',
              cursor: 'pointer',
              fontSize: '14px',
              fontWeight: 600
            }}
          >
            Reload Application
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
