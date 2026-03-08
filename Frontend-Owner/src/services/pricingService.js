import api from './api';

const pricingService = {
  // Get all pricing rules for a court
  getCourtPricing: async (courtId) => {
    const response = await api.get(`/api/courts/${courtId}/pricing`);
    return response.data;
  },

  // Create a new pricing rule
  createPricing: async (courtId, pricingData) => {
    const response = await api.post(`/api/courts/${courtId}/pricing`, pricingData);
    return response.data;
  },

  // Update a pricing rule
  updatePricing: async (pricingId, pricingData) => {
    const response = await api.patch(`/api/pricing/${pricingId}`, pricingData);
    return response.data;
  },

  // Delete a pricing rule
  deletePricing: async (pricingId) => {
    const response = await api.delete(`/api/pricing/${pricingId}`);
    return response.data;
  }
};

export default pricingService;
