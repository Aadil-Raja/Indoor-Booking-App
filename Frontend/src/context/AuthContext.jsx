import { createContext, useState, useEffect } from 'react';
import { tokenManager } from '../utils/tokenManager';

export const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Check if user is already logged in
    const storedUser = tokenManager.getUser();
    if (storedUser) {
      setUser(storedUser);
    }
    setLoading(false);
  }, []);

  const login = (token, userData) => {
    tokenManager.clearAuth(); // Clear old data
    tokenManager.setAuth(token, userData);
    setUser(userData);
  };

  const logout = () => {
    tokenManager.clearAuth();
    setUser(null);
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
