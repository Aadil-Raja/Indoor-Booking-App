import { apiClient } from './client';

export const getProperties = async () => {
    const response = await apiClient.get('/properties');
    return response.data;
};

export const deleteProperty = async (id: number) => {
    const response = await apiClient.delete(`/properties/${id}`);
    return response.data;
};
