import axios from 'axios';
import * as SecureStore from 'expo-secure-store';
import { Platform } from 'react-native';

const API_URL = process.env.EXPO_PUBLIC_API_URL || 'http://10.0.2.2:8001/api';

export const apiClient = axios.create({
    baseURL: API_URL,
    timeout: 15000,
    headers: { 'Content-Type': 'application/json' },
});

// Auto-attach bearer token (SecureStore only works on native, not web)
apiClient.interceptors.request.use(async (config) => {
    try {
        if (Platform.OS !== 'web') {
            const token = await SecureStore.getItemAsync('auth_token');
            if (token) config.headers.Authorization = `Bearer ${token}`;
        }
    } catch (e) {
        // Do not block the request if token fetch fails
        console.warn('[apiClient] Token fetch failed:', e);
    }
    return config;
});

// Response error logger for easier debugging
apiClient.interceptors.response.use(
    (response) => response,
    (error) => {
        console.error(
            '[apiClient] Error:',
            error?.response?.status,
            error?.response?.data ?? error?.message,
        );
        return Promise.reject(error);
    },
);
