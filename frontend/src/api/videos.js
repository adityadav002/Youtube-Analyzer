import axios from 'axios';
import { API_BASE_URL } from '../constants';

const api = axios.create({
  baseURL: `${API_BASE_URL}/videos`,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const getVideos = async (params = {}) => {
  const response = await api.get('', { params });
  return response.data;
};

export const getVideo = async (id) => {
  const response = await api.get(`/${id}`);
  return response.data;
};

export const extractMetadata = async (id) => {
  const response = await api.post(`/${id}/extract`);
  return response.data;
};

export const deleteVideo = async (id) => {
  const response = await api.delete(`/${id}`);
  return response.data;
};

export const importVideo = async (videoIdOrUrl) => {
  const response = await api.post('', { video_id: videoIdOrUrl });
  return response.data;
};

