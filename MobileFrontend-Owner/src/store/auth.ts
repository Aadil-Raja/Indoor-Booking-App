import { create } from 'zustand';
import * as SecureStore from 'expo-secure-store';

interface User {
    name: string;
    email?: string;
}

interface AuthState {
    token: string | null;
    user: User | null;
    isLoading: boolean;
    setAuth: (token: string, user: User) => Promise<void>;
    logout: () => Promise<void>;
    checkAuth: () => Promise<void>;
}

export const useAuthStore = create<AuthState>((set) => ({
    token: null,
    user: null,
    isLoading: true,
    setAuth: async (token, user) => {
        await SecureStore.setItemAsync('auth_token', token);
        await SecureStore.setItemAsync('user_data', JSON.stringify(user));
        set({ token, user });
    },
    logout: async () => {
        await SecureStore.deleteItemAsync('auth_token');
        await SecureStore.deleteItemAsync('user_data');
        set({ token: null, user: null });
    },
    checkAuth: async () => {
        try {
            const token = await SecureStore.getItemAsync('auth_token');
            const userData = await SecureStore.getItemAsync('user_data');
            if (token && userData) {
                set({ token, user: JSON.parse(userData), isLoading: false });
            } else {
                set({ token: null, user: null, isLoading: false });
            }
        } catch (e) {
            set({ token: null, user: null, isLoading: false });
        }
    },
}));
