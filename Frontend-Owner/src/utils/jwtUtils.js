// JWT token utilities
export const jwtUtils = {
  // Decode JWT token without verification (client-side only)
  decodeToken(token) {
    try {
      if (!token) return null;
      
      const parts = token.split('.');
      if (parts.length !== 3) return null;
      
      const payload = parts[1];
      const decoded = JSON.parse(atob(payload));
      return decoded;
    } catch (error) {
      console.error('Failed to decode token:', error);
      return null;
    }
  },

  // Get user info from token
  getUserFromToken(token) {
    const decoded = this.decodeToken(token);
    if (!decoded) return null;

    return {
      id: decoded.sub || decoded.user_id,
      email: decoded.email,
      role: decoded.role,
      name: decoded.name
    };
  },

  // Check if token is expired
  isTokenExpired(token) {
    const decoded = this.decodeToken(token);
    if (!decoded || !decoded.exp) return true;

    const currentTime = Date.now() / 1000;
    return decoded.exp < currentTime;
  }
};
