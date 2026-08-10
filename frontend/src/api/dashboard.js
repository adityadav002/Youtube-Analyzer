import axios from 'axios';
import { API_BASE_URL } from '../constants';

const api = axios.create({
  baseURL: `${API_BASE_URL}/dashboard`,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const getDashboardStats = async () => {
  const response = await api.get('/stats');
  return response.data;
};
