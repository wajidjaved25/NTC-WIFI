import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to add auth token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor to handle errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// Auth APIs
export const authAPI = {
  login: (username, password) => {
    const formData = new URLSearchParams();
    formData.append('username', username);
    formData.append('password', password);
    return api.post('/auth/login', formData, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
    });
  },
  requestOTP: (mobile) => 
    api.post('/auth/request-otp', { mobile }),
  verifyOTP: (mobile, otp) => 
    api.post('/auth/verify-otp', { mobile, otp }),
  getMe: () => 
    api.get('/auth/me'),
  createAdmin: (data) => 
    api.post('/auth/create-admin', data),
  listAdmins: () => 
    api.get('/auth/admins'),
  deactivateAdmin: (id) => 
    api.patch(`/auth/admins/${id}/deactivate`),
};

// Dashboard APIs
export const dashboardAPI = {
  getOverview: (days = 30) => 
    api.get(`/dashboard/overview?days=${days}`),
  getSessionsChart: (days = 7) => 
    api.get(`/dashboard/sessions-chart?days=${days}`),
  getDataUsageChart: (days = 7) => 
    api.get(`/dashboard/data-usage-chart?days=${days}`),
  getTopUsers: (limit = 10) => 
    api.get(`/dashboard/top-users?limit=${limit}`),
  getPeakHours: (days = 7) => 
    api.get(`/dashboard/peak-hours?days=${days}`),
  getAdPerformance: (days = 30) => 
    api.get(`/dashboard/ad-performance?days=${days}`),
  getRealTimeStats: () => 
    api.get('/dashboard/real-time'),
};

// Omada APIs
export const omadaAPI = {
  getConfig: () => 
    api.get('/omada/config'),
  updateConfig: (data) => 
    api.put('/omada/config', data),
  testConnection: (data) => 
    api.post('/omada/test-connection', data),
  getSites: () => 
    api.get('/omada/sites'),
  getClients: () => 
    api.get('/omada/clients'),
  authorizeClient: (data) => 
    api.post('/omada/authorize-client', data),
  unauthorizeClient: (mac) => 
    api.post('/omada/unauthorize-client', { mac }),
};

// Records APIs
export const recordsAPI = {
  getSessions: (params) => 
    api.get('/records/sessions', { params }),
  getSession: (id) => 
    api.get(`/records/sessions/${id}`),
  exportSessions: (params, format = 'excel') => 
    api.get(`/records/export/${format}`, { 
      params, 
      responseType: 'blob' 
    }),
  getUsers: (params) => 
    api.get('/records/users', { params }),
  blockUser: (id, reason) => 
    api.post(`/records/users/${id}/block`, { reason }),
  unblockUser: (id) => 
    api.post(`/records/users/${id}/unblock`),
};

// Advertisement APIs
export const adAPI = {
  getAds: (params) => 
    api.get('/ads', { params }),
  getAd: (id) => 
    api.get(`/ads/${id}`),
  createAd: (formData) => 
    api.post('/ads', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    }),
  updateAd: (id, data) => 
    api.put(`/ads/${id}`, data),
  deleteAd: (id) => 
    api.delete(`/ads/${id}`),
  uploadFile: (formData) => 
    api.post('/ads/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    }),
  toggleAd: (id) => 
    api.patch(`/ads/${id}/toggle`),
  updateOrder: (ads) => 
    api.post('/ads/update-order', { ads }),
};

// Portal Design APIs
export const portalAPI = {
  getDesign: () => 
    api.get('/portal/design'),
  updateDesign: (data) => 
    api.put('/portal/design', data),
  uploadLogo: (formData) => 
    api.post('/portal/upload-logo', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    }),
  uploadBackground: (formData) => 
    api.post('/portal/upload-background', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    }),
  getSettings: () => 
    api.get('/portal/settings'),
  updateSettings: (key, value) => 
    api.put('/portal/settings', { key, value }),
};

export default api;
