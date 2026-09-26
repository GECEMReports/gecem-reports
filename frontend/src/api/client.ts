import axios from 'axios';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/api',
});

export const API_BASE_URL = import.meta.env.VITE_API_URL || '/api';

export function getApiUrl(path: string): string {
  const normalizedPath = path.startsWith('/') ? path : `/${path}`;
  const base = API_BASE_URL.replace(/\/$/, '');
  if (normalizedPath.startsWith('/api/') && base.endsWith('/api')) {
    return `${base.slice(0, -'/api'.length)}${normalizedPath}`;
  }
  return `${base}${normalizedPath}`;
}

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  const tenantId = localStorage.getItem('tenantId');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  if (tenantId) {
    config.headers['X-Tenant-ID'] = tenantId;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token');
      localStorage.removeItem('tenantId');
      localStorage.removeItem('userId');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  },
);

export default api;
