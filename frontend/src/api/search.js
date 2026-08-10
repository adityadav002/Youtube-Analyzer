import axios from 'axios';
import { API_BASE_URL } from '../constants';

const api = axios.create({
  baseURL: `${API_BASE_URL}/search`,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const searchYoutube = async (q, type = 'video', maxResults = 20, refresh = false) => {
  const response = await api.get('/youtube', {
    params: { q, type, max_results: maxResults, refresh }
  });
  return response.data;
};

export const searchInternal = async (params = {}) => {
  const response = await api.get('/internal', { params });
  return response.data;
};

export const getSearchHistory = async () => {
  const response = await api.get('/history');
  return response.data;
};
