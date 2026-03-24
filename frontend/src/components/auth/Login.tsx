import React, { useState } from 'react';
import { useAuth } from '../../context/AuthContext';
import { Lock, User, AlertCircle, ArrowRight } from 'lucide-react';
import './Login.css';

export const Login: React.FC = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const { login } = useAuth();

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsLoading(true);
    
    try {
      await login(email, password);
    } catch (err: any) {
      setError(err.message || 'Invalid credentials');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="login-container">
      <div className="login-card">
        <div className="login-header">
          <div className="logo-placeholder">F</div>
          <h2>Fiscalogix</h2>
          <p>Enterprise Decision Command Center</p>
        </div>
        
        {error && (
          <div className="login-alert">
            <AlertCircle size={16} />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleLogin} className="login-form">
          <div className="input-group">
            <label>Work Email</label>
            <div className="input-wrapper">
              <User size={18} className="input-icon" />
              <input 
                type="email" 
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="admin@fiscalogix.com"
                required
              />
            </div>
          </div>
          
          <div className="input-group">
            <label>Password</label>
            <div className="input-wrapper">
              <Lock size={18} className="input-icon" />
              <input 
                type="password" 
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                required
              />
            </div>
          </div>
          
          <button type="submit" className="login-btn" disabled={isLoading}>
            {isLoading ? 'Authenticating...' : (
              <>
                Sign In <ArrowRight size={16} />
              </>
            )}
          </button>
        </form>
        
        <div className="login-footer">
          <p>Demo Accounts: <br /> 
          <strong>admin@fiscalogix.com</strong> (Admin) <br /> 
          <strong>analyst@fiscalogix.com</strong> (Read-Only) <br />
          <em>PW: admin123 / analyst123</em></p>
        </div>
      </div>
    </div>
  );
};
