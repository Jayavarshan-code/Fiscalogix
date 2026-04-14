import React, { useState } from 'react';
import { useAuth } from '../../context/AuthContext';
import { Building2, Mail, Lock, ArrowRight, AlertCircle } from 'lucide-react';
import { API_BASE_URL } from '../../services/api';

const VERTICALS = [
  { value: 'seafood',       label: 'Seafood & Aquaculture' },
  { value: 'logistics',     label: 'Logistics & Transport' },
  { value: 'pharmaceutical',label: 'Pharmaceutical' },
  { value: 'fmcg',          label: 'FMCG / Consumer Goods' },
  { value: 'automotive',    label: 'Automotive' },
  { value: 'electronics',   label: 'Electronics' },
  { value: 'textile',       label: 'Textile & Apparel' },
  { value: 'industrial',    label: 'Industrial / Manufacturing' },
  { value: 'chemical',      label: 'Chemicals' },
];

interface RegisterProps {
  onSwitchToLogin: () => void;
}

export const Register: React.FC<RegisterProps> = ({ onSwitchToLogin }) => {
  const { login } = useAuth();
  const [form, setForm] = useState({
    company_name: '',
    email: '',
    password: '',
    industry_vertical: 'logistics',
  });
  const [error, setError]     = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const set = (k: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) =>
    setForm(f => ({ ...f, [k]: e.target.value }));

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      const resp = await fetch(`${API_BASE_URL}/auth/register`, {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify(form),
      });

      const data = await resp.json();
      if (!resp.ok) throw new Error(data.detail || 'Registration failed.');

      // Persist session identically to the login flow
      localStorage.setItem('access_token', data.access_token);
      localStorage.setItem('profile_name', data.profile_name);
      localStorage.setItem('email',        data.email);
      localStorage.setItem('user_id',      String(data.user_id));
      localStorage.setItem('permissions',  JSON.stringify(data.permissions || {}));

      // Trigger AuthContext so protected routes unlock immediately
      await login(form.email, form.password);
    } catch (err: any) {
      setError(err.message || 'Registration failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-container">
      <div className="login-card" style={{ maxWidth: 480 }}>
        <div className="login-header">
          <div className="logo-placeholder">F</div>
          <h2>Create Your Account</h2>
          <p>Start your 30-minute TTFV onboarding</p>
        </div>

        {error && (
          <div className="login-alert">
            <AlertCircle size={16} />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="login-form">
          <div className="input-group">
            <label>Company Name</label>
            <div className="input-wrapper">
              <Building2 size={18} className="input-icon" />
              <input
                type="text"
                value={form.company_name}
                onChange={set('company_name')}
                placeholder="Acme Logistics Pvt Ltd"
                required
              />
            </div>
          </div>

          <div className="input-group">
            <label>Work Email</label>
            <div className="input-wrapper">
              <Mail size={18} className="input-icon" />
              <input
                type="email"
                value={form.email}
                onChange={set('email')}
                placeholder="cfo@yourcompany.com"
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
                value={form.password}
                onChange={set('password')}
                placeholder="Min. 8 characters"
                required
                minLength={8}
              />
            </div>
          </div>

          <div className="input-group">
            <label>Industry Vertical</label>
            <div className="input-wrapper">
              <select
                value={form.industry_vertical}
                onChange={set('industry_vertical')}
                style={{ background: 'transparent', border: 'none', width: '100%', color: 'inherit', paddingLeft: 8 }}
              >
                {VERTICALS.map(v => (
                  <option key={v.value} value={v.value}>{v.label}</option>
                ))}
              </select>
            </div>
          </div>

          <button type="submit" className="login-btn" disabled={loading}>
            {loading ? 'Creating account...' : (
              <>Create Account & Start Onboarding <ArrowRight size={16} /></>
            )}
          </button>
        </form>

        <div className="login-footer">
          <p>Already have an account?{' '}
            <button
              onClick={onSwitchToLogin}
              style={{ background: 'none', border: 'none', color: 'var(--brand-primary)', cursor: 'pointer' }}
            >
              Sign in
            </button>
          </p>
        </div>
      </div>
    </div>
  );
};
