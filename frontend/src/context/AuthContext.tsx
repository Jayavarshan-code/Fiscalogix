import React, { createContext, useContext, useState, useEffect } from 'react';
import { API_BASE_URL } from '../services/api';

interface UserPayload {
  id: number;
  email: string;
  profileName: string;
  permissions: any;
}

interface AuthContextType {
  currentUser: UserPayload | null;
  login: (email: string, pass: string) => Promise<void>;
  logout: () => void;
  hasPermission: (perm: string) => boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [currentUser, setCurrentUser] = useState<UserPayload | null>(null);

  useEffect(() => {
    const token = localStorage.getItem('access_token');
    const profileName = localStorage.getItem('profile_name');
    const email = localStorage.getItem('email');
    const userId = localStorage.getItem('user_id');
    
    if (token && email) {
      // Mocking profile permissions in frontend since they aren't fully returned yet from API
      // In production, the backend /auth/me route would return the full permissions block
      const perms = profileName === 'System Admin' 
        ? { can_view: true, can_execute: true } 
        : { can_view: true, can_execute: false };

      setCurrentUser({
        id: Number(userId) || 1,
        email,
        profileName: profileName || 'System Admin',
        permissions: perms
      });
    }
  }, []);

  const login = async (email: string, pass: string) => {
    const formData = new URLSearchParams();
    formData.append('username', email);
    formData.append('password', pass);

    const resp = await fetch(`${API_BASE_URL}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: formData.toString()
    });

    if (!resp.ok) {
      const err = await resp.json();
      throw new Error(err.detail || 'Login failed. Please check your credentials.');
    }

    const data = await resp.json();

    // Store the REAL JWT from the backend
    localStorage.setItem('access_token', data.access_token);
    localStorage.setItem('profile_name', data.profile_name);
    localStorage.setItem('email', data.email);
    localStorage.setItem('user_id', String(data.user_id));

    const perms = data.profile_name === 'System Admin'
      ? { can_view: true, can_execute: true }
      : { can_view: true, can_execute: false };

    setCurrentUser({
      id: data.user_id,
      email: data.email,
      profileName: data.profile_name,
      permissions: perms
    });
  };

  const logout = () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('profile_name');
    localStorage.removeItem('email');
    localStorage.removeItem('user_id');
    setCurrentUser(null);
  };

  const hasPermission = (perm: string) => {
    if (!currentUser || !currentUser.permissions) return false;
    return currentUser.permissions[perm as keyof UserPayload['permissions']] === true;
  };

  return (
    <AuthContext.Provider value={{ currentUser, login, logout, hasPermission }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

