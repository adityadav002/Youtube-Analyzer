import { apiClient } from '../client';

export const getChannels = async (params) => {
  const { data } = await apiClient.get('/channels', { params });
  return data;
};

export const getChannel = async (id) => {
  const { data } = await apiClient.get(`/channels/${id}`);
  return data;
};

export const addChannel = async (url) => {
  const { data } = await apiClient.post('/channels', { url });
  return data;
};

export const updateChannel = async (id, payload) => {
  const { data } = await apiClient.patch(`/channels/${id}`, payload);
  return data;
};

export const deleteChannel = async (id) => {
  await apiClient.delete(`/channels/${id}?confirm=true`);
};

export const refreshChannel = async (id) => {
  const { data } = await apiClient.post(`/channels/${id}/refresh`);
  return data;
};
