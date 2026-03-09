import { apiClient } from './client';

export const loginWithPassword = async (email: string, password: string) => {
    const response = await apiClient.post('/auth/login/password', { email, password });
    return response.data;
};

export const signUp = async (data: any) => {
    const response = await apiClient.post('/auth/signup', data);
    return response.data;
};

export const verifyCode = async (email: string, code: string) => {
    const response = await apiClient.post('/auth/verify-code', { email, code });
    return response.data;
};

export const requestCode = async (email: string) => {
    const response = await apiClient.post('/auth/request-code', { email });
    return response.data;
};

export const loginRequestCode = async (email: string) => {
    const response = await apiClient.post('/auth/login/request-code', { email });
    return response.data;
};

export const loginVerifyCode = async (email: string, code: string) => {
    const response = await apiClient.post('/auth/login/verify-code', { email, code });
    return response.data;
};
