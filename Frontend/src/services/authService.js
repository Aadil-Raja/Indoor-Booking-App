import api from './api';

export const authService = {
  // Signup
  async signup(email, password, name) {
    try {
      const response = await api.post('/api/auth/signup', {
        email,
        password,
        name,
        role: 'owner'
      });
      return response.data;
    } catch (error) {
      throw error;
    }
  },

  // Verify email OTP
  async verifyCode(email, code) {
    try {
      const response = await api.post('/api/auth/verify-code', {
        email,
        code
      });
      return response.data;
    } catch (error) {
      throw error;
    }
  },

  // Login with password
  async loginPassword(email, password) {
    try {
      const response = await api.post('/api/auth/login/password', {
        email,
        password
      });
      return response.data;
    } catch (error) {
      throw error;
    }
  },

  // Request new OTP
  async requestCode(email) {
    try {
      const response = await api.post('/api/auth/request-code', {
        email
      });
      return response.data;
    } catch (error) {
      throw error;
    }
  }
};
