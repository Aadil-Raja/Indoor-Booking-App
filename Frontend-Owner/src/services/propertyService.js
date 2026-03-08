import api from './api';

export const propertyService = {
  // Get all properties for current owner
  async getProperties() {
    try {
      const response = await api.get('/api/properties');
      return response.data;
    } catch (error) {
      throw error;
    }
  },

  // Get property details with courts
  async getPropertyDetails(propertyId) {
    try {
      const response = await api.get(`/api/properties/${propertyId}`);
      return response.data;
    } catch (error) {
      throw error;
    }
  },

  // Create new property
  async createProperty(data) {
    try {
      const response = await api.post('/api/properties', data);
      return response.data;
    } catch (error) {
      throw error;
    }
  },

  // Update property
  async updateProperty(propertyId, data) {
    try {
      const response = await api.patch(`/api/properties/${propertyId}`, data);
      return response.data;
    } catch (error) {
      throw error;
    }
  },

  // Delete property
  async deleteProperty(propertyId) {
    try {
      const response = await api.delete(`/api/properties/${propertyId}`);
      return response.data;
    } catch (error) {
      throw error;
    }
  }
};
