import axios from 'axios';

// Backend URL: uses VITE_API_URL if specified, otherwise uses relative /api/v1 for both local proxy and production
const API_BASE_URL = import.meta.env.VITE_API_URL || '/api/v1';

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
});

// Attach JWT to every request
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('infraguard_access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Auto-refresh on 401
let isRefreshing = false;
let failedQueue = [];

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    if (
      error.response?.status === 401 &&
      !originalRequest._retry &&
      !originalRequest.url.includes('/auth/login') &&
      !originalRequest.url.includes('/auth/refresh')
    ) {
      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject });
        }).then((token) => {
          originalRequest.headers.Authorization = `Bearer ${token}`;
          return api(originalRequest);
        });
      }

      originalRequest._retry = true;
      isRefreshing = true;
      const refreshToken = localStorage.getItem('infraguard_refresh_token');
      if (!refreshToken) {
        localStorage.removeItem('infraguard_access_token');
        localStorage.removeItem('infraguard_refresh_token');
        localStorage.removeItem('infraguard_user');
        window.location.href = '/login';
        return Promise.reject(error);
      }

      try {
        const { data } = await axios.post(`${API_BASE_URL}/auth/refresh`, {
          refresh_token: refreshToken,
        });
        localStorage.setItem('infraguard_access_token', data.access_token);
        localStorage.setItem('infraguard_refresh_token', data.refresh_token);
        api.defaults.headers.Authorization = `Bearer ${data.access_token}`;
        failedQueue.forEach((p) => p.resolve(data.access_token));
        failedQueue = [];
        originalRequest.headers.Authorization = `Bearer ${data.access_token}`;
        return api(originalRequest);
      } catch (err) {
        failedQueue.forEach((p) => p.reject(err));
        failedQueue = [];
        localStorage.removeItem('infraguard_access_token');
        localStorage.removeItem('infraguard_refresh_token');
        localStorage.removeItem('infraguard_user');
        window.location.href = '/login';
        return Promise.reject(err);
      } finally {
        isRefreshing = false;
      }
    }
    return Promise.reject(error);
  }
);

export default api;
