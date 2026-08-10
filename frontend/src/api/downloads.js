import { apiClient } from '../client';

export const getDownloads = async () => {
  const { data } = await apiClient.get('/downloads');
  return data;
};

export const startDownload = async (payload) => {
  const { data } = await apiClient.post('/downloads', payload);
  return data;
};

export const cancelDownload = async (id) => {
  const { data } = await apiClient.post(`/downloads/${id}/cancel`);
  return data;
};

export const retryDownload = async (id) => {
  const { data } = await apiClient.post(`/downloads/${id}/retry`);
  return data;
};

export const deleteDownload = async (id, deleteFile = false) => {
  await apiClient.delete(`/downloads/${id}?delete_file=${deleteFile}`);
};

export const openFileLocation = async (id) => {
  await apiClient.post(`/downloads/${id}/open`);
};
