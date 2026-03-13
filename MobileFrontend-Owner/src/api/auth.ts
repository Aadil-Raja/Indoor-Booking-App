import { apiClient } from './client';

export const loginWithPassword = async (email: string, password: string) => {
    const response = await apiClient.post('/auth/login/password', { email, password });
    return response.data;
};

export const signUp = async (name: string, email: string, password: string, role = 'owner') => {
    const response = await apiClient.post('/auth/signup', { name, email, password, role });
    return response.data;
};

/** Verify OTP after signup — returns access_token on success */
export const verifyCode = async (email: string, code: string) => {
    const response = await apiClient.post('/auth/verify-code', { email, code });
    return response.data;
};

/** Resend OTP to email */
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
