// Token management utility for localStorage
// Using unique prefixed keys to avoid conflicts with other apps
const TOKEN_KEY = 'courthub_owner_token';

export const tokenManager = {
  // Get token from localStorage
  getToken() {
    return localStorage.getItem(TOKEN_KEY);
  },

  // Set token
  setToken(token) {
    localStorage.setItem(TOKEN_KEY, token);
  },

  // Clear token
  clearToken() {
    localStorage.removeItem(TOKEN_KEY);
  },

  // Check if user is authenticated
  isAuthenticated() {
    return !!this.getToken();
  }
};
