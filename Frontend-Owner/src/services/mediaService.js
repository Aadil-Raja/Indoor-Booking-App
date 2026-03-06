import api from './api';

export const mediaService = {
  // Upload property media
  async uploadPropertyMedia(propertyId, file, mediaType, caption = '', displayOrder = 0) {
    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('media_type', mediaType);
      if (caption) formData.append('caption', caption);
      formData.append('display_order', displayOrder);

      const response = await api.post(
        `/api/properties/${propertyId}/media`,
        formData,
        {
          headers: {
            'Content-Type': 'multipart/form-data'
          }
        }
      );
      return response.data;
    } catch (error) {
      throw error;
    }
  },

  // Upload court media
  async uploadCourtMedia(courtId, file, mediaType, caption = '', displayOrder = 0) {
    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('media_type', mediaType);
      if (caption) formData.append('caption', caption);
      formData.append('display_order', displayOrder);

      const response = await api.post(
        `/api/courts/${courtId}/media`,
        formData,
        {
          headers: {
            'Content-Type': 'multipart/form-data'
          }
        }
      );
      return response.data;
    } catch (error) {
      throw error;
    }
  },

  // Get property media
  async getPropertyMedia(propertyId) {
    try {
      const response = await api.get(`/api/properties/${propertyId}/media`);
      return response.data;
    } catch (error) {
      throw error;
    }
  },

  // Get court media
  async getCourtMedia(courtId) {
    try {
      const response = await api.get(`/api/courts/${courtId}/media`);
      return response.data;
    } catch (error) {
      throw error;
    }
  },

  // Update media
  async updateMedia(mediaId, data) {
    try {
      const response = await api.patch(`/api/media/${mediaId}`, data);
      return response.data;
    } catch (error) {
      throw error;
    }
  },

  // Delete media
  async deleteMedia(mediaId) {
    try {
      const response = await api.delete(`/api/media/${mediaId}`);
      return response.data;
    } catch (error) {
      throw error;
    }
  }
};
