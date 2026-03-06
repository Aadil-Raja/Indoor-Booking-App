import api from './api';

export const publicService = {
  // Search properties with courts
  async searchCourts(params = {}) {
    try {
      const queryParams = new URLSearchParams();
      
      if (params.search) queryParams.append('search', params.search);
      if (params.date) queryParams.append('date', params.date);
      if (params.start_time) queryParams.append('start_time', params.start_time);
      if (params.sport_type) queryParams.append('sport_type', params.sport_type);
      if (params.min_price) queryParams.append('min_price', params.min_price);
      if (params.max_price) queryParams.append('max_price', params.max_price);
      
      const response = await api.get(`/api/public/properties?${queryParams.toString()}`);
      return response.data;
    } catch (error) {
      throw error;
    }
  },

  // Get court details by ID
  async getCourtDetails(courtId) {
    try {
      // Add timestamp to bypass cache
      const response = await api.get(`/api/public/courts/${courtId}`, {
        params: { _t: Date.now() }
      });
      return response.data;
    } catch (error) {
      throw error;
    }
  },

  // Get available slots for a court on a specific date
  async getAvailableSlots(courtId, date) {
    try {
      const response = await api.get(`/api/public/courts/${courtId}/available-slots`, {
        params: { date }
      });
      return response.data;
    } catch (error) {
      throw error;
    }
  }
};
