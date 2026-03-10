import { apiClient } from './client';

export const getDashboard = async () => {
    const response = await apiClient.get('/owner/dashboard');
    return response.data;
};

export const getOwnerProfile = async () => {
    const response = await apiClient.get('/owner/profile');
    return response.data;
};
