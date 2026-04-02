import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { authApi } from '../utils/api';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    try {
      const stored = localStorage.getItem('byos_user');
      return stored ? JSON.parse(stored) : null;
    } catch {
      return null;
    }
  });
  const [token, setToken] = useState(() => localStorage.getItem('byos_token') || null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const login = useCallback(async (email, password) => {
    setLoading(true);
    setError(null);
    try {
      const res = await authApi.login(email, password);
      const { access_token, user_id, workspace_id, email: userEmail } = res.data;
      const userData = { id: user_id, email: userEmail, workspace_id };
      localStorage.setItem('byos_token', access_token);
      localStorage.setItem('byos_user', JSON.stringify(userData));
      setToken(access_token);
      setUser(userData);
      return { success: true };
    } catch (err) {
      const msg = err.response?.data?.detail || 'Login failed';
      setError(msg);
      return { success: false, error: msg };
    } finally {
      setLoading(false);
    }
  }, []);

  const register = useCallback(async (email, password, fullName) => {
    setLoading(true);
    setError(null);
    try {
      await authApi.register(email, password, fullName);
      return await login(email, password);
    } catch (err) {
      const msg = err.response?.data?.detail || 'Registration failed';
      setError(msg);
      return { success: false, error: msg };
    } finally {
      setLoading(false);
    }
  }, [login]);

  const logout = useCallback(() => {
    localStorage.removeItem('byos_token');
    localStorage.removeItem('byos_user');
    setToken(null);
    setUser(null);
  }, []);

  const isAuthenticated = Boolean(token && user);

  return (
    <AuthContext.Provider value={{ user, token, loading, error, login, register, logout, isAuthenticated }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider');
  return ctx;
}
