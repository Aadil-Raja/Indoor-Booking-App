import { createContext, useState, useEffect } from 'react';
import { tokenManager } from '../utils/tokenManager';

export const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Check if token exists
    const token = tokenManager.getToken();

    if (token) {
      // Token exists, user is authenticated
      setUser({ authenticated: true });
    }
    setLoading(false);
  }, []);

  const login = (token) => {
    tokenManager.setToken(token);
    setUser({ authenticated: true });

    // Check for redirect URL
    const redirectUrl = sessionStorage.getItem('redirectAfterLogin');
    if (redirectUrl) {
      sessionStorage.removeItem('redirectAfterLogin');
      window.location.href = redirectUrl;
    }
  };

  const logout = () => {
    tokenManager.clearToken();
    setUser(null);
    window.location.href = '/owner/login';
  };

  const value = {
    user,
    login,
    logout,
    isAuthenticated: !!user,
    loading
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};
