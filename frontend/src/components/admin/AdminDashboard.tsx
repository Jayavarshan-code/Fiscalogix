import React, { useState, useEffect } from 'react';
import { Users, Shield, Plus } from 'lucide-react';
import { API_BASE_URL } from '../../services/api';
import './AdminDashboard.css';

interface UserData {
  id: number;
  email: string;
  profile_name: string;
  role_name: string;
  tenant_id: string;
}

interface ProfileData {
  id: number;
  name: string;
}

interface RoleData {
  id: number;
  name: string;
  permissions: Record<string, boolean>;
}

const getAuthHeader = (): Record<string, string> => {
  const token = localStorage.getItem('access_token');
  return token ? { 'Authorization': `Bearer ${token}` } : {};
};

export const AdminDashboard: React.FC = () => {
  const [users, setUsers] = useState<UserData[]>([]);
  const [profiles, setProfiles] = useState<ProfileData[]>([]);
  const [roles, setRoles] = useState<RoleData[]>([]);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [createError, setCreateError] = useState('');

  // New User Form State
  const [newEmail, setNewEmail] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [newProfileId, setNewProfileId] = useState<number | ''>('');
  const [newRoleId, setNewRoleId] = useState<number | ''>('');

  useEffect(() => {
    fetchUsers();
    fetchProfiles();
    fetchRoles();
  }, []);

  const fetchUsers = async () => {
    try {
      const resp = await fetch(`${API_BASE_URL}/admin/users`, {
        headers: getAuthHeader()
      });
      if (resp.ok) {
        setUsers(await resp.json());
      }
    } catch(e) { console.error('Failed to fetch users', e); }
  };

  const fetchProfiles = async () => {
    try {
      const resp = await fetch(`${API_BASE_URL}/admin/profiles`, {
        headers: getAuthHeader()
      });
      if (resp.ok) {
        setProfiles(await resp.json());
      }
    } catch(e) { console.error('Failed to fetch profiles', e); }
  };

  const fetchRoles = async () => {
    try {
      const resp = await fetch(`${API_BASE_URL}/admin/roles`, {
        headers: getAuthHeader()
      });
      if (resp.ok) {
        setRoles(await resp.json());
      }
    } catch(e) { console.error('Failed to fetch roles', e); }
  };

  const handleCreateUser = async (e: React.SyntheticEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!newProfileId || !newRoleId) {
      setCreateError('Profile and Role are required.');
      return;
    }
    setCreateError('');

    try {
      const resp = await fetch(`${API_BASE_URL}/admin/users`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...getAuthHeader() },
        body: JSON.stringify({
          username: newEmail,
          password: newPassword,
          profile_id: Number(newProfileId),
          role_id: Number(newRoleId),
        })
      });

      if (resp.ok) {
        setShowCreateModal(false);
        setNewEmail('');
        setNewPassword('');
        setNewProfileId('');
        setNewRoleId('');
        fetchUsers();
      } else {
        const err = await resp.json();
        setCreateError(err.detail || 'Failed to create user.');
      }
    } catch(e) {
      console.error(e);
      setCreateError('Network error. Please try again.');
    }
  };

  return (
    <div className="admin-dashboard p-6">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2"><Shield size={24} className="text-brand-primary" /> Admin &amp; Global Settings</h1>
          <p className="text-[var(--text-secondary)] text-sm mt-1">Manage global preferences, tenant users, and security policies.</p>
        </div>
        <div className="flex gap-3">
          <button
            className="btn-outline flex items-center gap-2"
            onClick={() => {
              const root = document.documentElement;
              root.classList.toggle('dark');
            }}
          >
            🌓 Toggle Interface Theme
          </button>
          <button
            className="btn-primary flex items-center gap-2"
            onClick={() => setShowCreateModal(true)}
          >
            <Plus size={16} /> Provision User
          </button>
        </div>
      </div>

      <div className="dashboard-card">
        <h3 className="card-title flex items-center gap-2 mb-4"><Users size={18} /> Directory</h3>
        <table className="data-table w-full">
          <thead>
            <tr>
              <th>ID</th>
              <th>Work Email</th>
              <th>Assigned Profile</th>
              <th>Role</th>
              <th>Tenant</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {users.map(u => (
              <tr key={u.id}>
                <td>{u.id}</td>
                <td className="font-medium text-primary">{u.email}</td>
                <td>
                  <span className={`badge ${u.profile_name === 'System Admin' ? 'badge-primary' : 'badge-outline'}`}>
                    {u.profile_name}
                  </span>
                </td>
                <td>
                  <span className="badge badge-outline">{u.role_name || '—'}</span>
                </td>
                <td className="text-sm text-secondary">{u.tenant_id}</td>
                <td><span className="badge badge-success">Active</span></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {showCreateModal && (
        <div className="modal-overlay" onClick={() => setShowCreateModal(false)}>
          <div className="modal-content" onClick={e => e.stopPropagation()}>
            <h3 className="text-xl font-bold mb-4">Provision New User</h3>
            <form onSubmit={handleCreateUser}>
              <div className="input-group">
                <label>Work Email</label>
                <input required type="email" placeholder="jane@fiscalogix.com" value={newEmail} onChange={e => setNewEmail(e.target.value)} />
              </div>
              <div className="input-group">
                <label>Password</label>
                <input required type="password" placeholder="Temporary password" value={newPassword} onChange={e => setNewPassword(e.target.value)} />
              </div>
              <div className="input-group">
                <label>Security Profile</label>
                <select required value={newProfileId} onChange={e => setNewProfileId(Number(e.target.value))}>
                  <option value="" disabled>Select Profile...</option>
                  {profiles.map(p => (
                    <option key={p.id} value={p.id}>{p.name}</option>
                  ))}
                </select>
              </div>
              <div className="input-group">
                <label>Role</label>
                <select required value={newRoleId} onChange={e => setNewRoleId(Number(e.target.value))}>
                  <option value="" disabled>Select Role...</option>
                  {roles.map(r => (
                    <option key={r.id} value={r.id}>{r.name}</option>
                  ))}
                </select>
              </div>
              {createError && (
                <div className="text-critical text-sm mt-2 mb-2">{createError}</div>
              )}
              <div className="flex justify-end gap-3 mt-6">
                <button type="button" className="btn-outline" onClick={() => setShowCreateModal(false)}>Cancel</button>
                <button type="submit" className="btn-primary">Create User</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
