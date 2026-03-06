import api from './api';

export const courtService = {
  // Get all courts for a property
  async getPropertyCourts(propertyId) {
    try {
      const response = await api.get(`/api/properties/${propertyId}/courts`);
      return response.data;
    } catch (error) {
      throw error;
    }
  },

  // Get court details
  async getCourtDetails(courtId) {
    try {
      const response = await api.get(`/api/courts/${courtId}`);
      return response.data;
    } catch (error) {
      throw error;
    }
  },

  // Create new court
  async createCourt(propertyId, data) {
    try {
      const response = await api.post(`/api/properties/${propertyId}/courts`, data);
      return response.data;
    } catch (error) {
      throw error;
    }
  },

  // Update court
  async updateCourt(courtId, data) {
    try {
      const response = await api.patch(`/api/courts/${courtId}`, data);
      return response.data;
    } catch (error) {
      throw error;
    }
  },

  // Delete court
  async deleteCourt(courtId) {
    try {
      const response = await api.delete(`/api/courts/${courtId}`);
      return response.data;
    } catch (error) {
      throw error;
    }
  }
};
