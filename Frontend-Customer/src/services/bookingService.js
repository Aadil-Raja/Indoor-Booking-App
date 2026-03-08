import api from './api';

export const bookingService = {
  // Create a new booking
  async createBooking(bookingData) {
    try {
      const response = await api.post('/api/bookings', bookingData);
      return response.data;
    } catch (error) {
      throw error;
    }
  },

  // Get user's bookings
  async getUserBookings(params = {}) {
    try {
      const queryParams = new URLSearchParams();
      
      if (params.status) queryParams.append('status', params.status);
      if (params.from_date) queryParams.append('from_date', params.from_date);
      if (params.to_date) queryParams.append('to_date', params.to_date);
      
      const response = await api.get(`/api/bookings?${queryParams.toString()}`);
      return response.data;
    } catch (error) {
      throw error;
    }
  },

  // Get booking details
  async getBookingDetails(bookingId) {
    try {
      const response = await api.get(`/api/bookings/${bookingId}`);
      return response.data;
    } catch (error) {
      throw error;
    }
  },

  // Upload payment screenshot
  async uploadPaymentProof(bookingId, file) {
    try {
      const formData = new FormData();
      formData.append('file', file);
      
      const response = await api.post(`/api/bookings/${bookingId}/payment-proof`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      });
      return response.data;
    } catch (error) {
      throw error;
    }
  },

  // Cancel booking
  async cancelBooking(bookingId) {
    try {
      const response = await api.patch(`/api/bookings/${bookingId}/cancel`);
      return response.data;
    } catch (error) {
      throw error;
    }
  }
};
