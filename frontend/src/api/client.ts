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

async function describePayload(data: unknown, status: number): Promise<string> {
  let text = '';
  if (data instanceof Blob) {
    try {
      text = await data.text();
    } catch {
      text = '';
    }
  } else if (typeof data === 'string') {
    text = data;
  }
  if (text) {
    try {
      const parsed = JSON.parse(text) as { detail?: unknown; message?: unknown };
      const detail = parsed.detail ?? parsed.message;
      if (typeof detail === 'string' && detail.trim()) {
        return detail;
      }
    } catch {
      if (!text.trim().startsWith('<')) {
        return text.trim().slice(0, 200);
      }
    }
  }
  return `El servidor no devolvió un PDF válido (HTTP ${status})`;
}

export async function fetchPdf(path: string): Promise<Blob> {
  try {
    const response = await api.get<Blob>(path, { responseType: 'blob' });
    const contentType = String(response.headers['content-type'] ?? '');
    if (!contentType.includes('application/pdf')) {
      throw new Error(await describePayload(response.data, response.status));
    }
    return response.data;
  } catch (error) {
    if (axios.isAxiosError(error) && error.response) {
      throw new Error(await describePayload(error.response.data, error.response.status));
    }
    throw error;
  }
}

export function openPdfInNewTab(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const opened = window.open(url, '_blank');
  if (opened) {
    try {
      opened.opener = null;
    } catch {
      // ignore
    }
  } else {
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = filename;
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
  }
  window.setTimeout(() => URL.revokeObjectURL(url), 60000);
}

export default api;
