import { createContext, useState, useEffect } from 'react';
import { tokenManager } from '../utils/tokenManager';
import { jwtUtils } from '../utils/jwtUtils';

export const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Check if token exists
    const token = tokenManager.getToken();

    if (token) {
      // Check if token is expired
      if (jwtUtils.isTokenExpired(token)) {
        tokenManager.clearToken();
        setUser(null);
      } else {
        // Decode token to get user info
        const userInfo = jwtUtils.getUserFromToken(token);
        if (userInfo) {
          setUser({ 
            authenticated: true,
            ...userInfo
          });
        } else {
          tokenManager.clearToken();
          setUser(null);
        }
      }
    }
    setLoading(false);
  }, []);

  const login = (token) => {
    tokenManager.setToken(token);
    
    // Decode token to get user info
    const userInfo = jwtUtils.getUserFromToken(token);
    if (userInfo) {
      setUser({ 
        authenticated: true,
        ...userInfo
      });
    }

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
    window.location.href = '/login';
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
