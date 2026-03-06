import api from './api';

export const ownerService = {
  // Get owner profile
  async getProfile() {
    try {
      const response = await api.get('/api/owner/profile');
      return response.data;
    } catch (error) {
      throw error;
    }
  },

  // Create or update owner profile
  async updateProfile(data) {
    try {
      const response = await api.post('/api/owner/profile', data);
      return response.data;
    } catch (error) {
      throw error;
    }
  },

  // Get dashboard stats
  async getDashboardStats() {
    try {
      const response = await api.get('/api/owner/dashboard');
      return response.data;
    } catch (error) {
      throw error;
    }
  }
};
