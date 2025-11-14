import axios from 'axios';

const API_BASE_URL = 'api';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Portal Design
export const getPortalDesign = async () => {
  const response = await api.get('/public/portal-design');
  return response.data;
};

// Get Active Ads
export const getActiveAds = async () => {
  const response = await api.get('/public/ads/active');
  return response.data;
};

// Track Ad Event
export const trackAdEvent = async (adId, eventType, sessionData = {}) => {
  const response = await api.post('/public/ads/track', {
    ad_id: adId,
    event_type: eventType,
    ...sessionData,
  });
  return response.data;
};

// Send OTP
export const sendOTP = async (mobile) => {
  const response = await api.post('/public/send-otp', { mobile });
  return response.data;
};

// Verify OTP
export const verifyOTP = async (mobile, otp) => {
  const response = await api.post('/public/verify-otp', { mobile, otp });
  return response.data;
};

// Register User
export const registerUser = async (userData) => {
  const response = await api.post('/public/register', userData);
  return response.data;
};

// Authorize WiFi Access
export const authorizeWiFi = async (authData) => {
  const response = await api.post('/public/authorize', authData);
  return response.data;
};

export default api;
