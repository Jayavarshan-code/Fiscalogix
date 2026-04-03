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
    // MOCK LOGIN FOR BROWSER DEMO
    localStorage.setItem('access_token', 'mock_token_123');
    localStorage.setItem('profile_name', 'System Admin');
    localStorage.setItem('email', email || 'admin@fiscalogix.com');
    localStorage.setItem('user_id', '1');

    setCurrentUser({
      id: 1,
      email: email || 'admin@fiscalogix.com',
      profileName: 'System Admin',
      permissions: { can_view: true, can_execute: true }
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

