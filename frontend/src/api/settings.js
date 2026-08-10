import { apiClient } from '../client';

export const getSettings = async () => {
  const { data } = await apiClient.get('/settings');
  return data;
};

export const updateSettings = async (payload) => {
  const { data } = await apiClient.put('/settings', payload);
  return data;
};

export const uploadCookiesFile = async (file) => {
  const formData = new FormData();
  formData.append('file', file);
  const { data } = await apiClient.post('/settings/cookies', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
  return data;
};

export const deleteCookiesFile = async () => {
  const { data } = await apiClient.delete('/settings/cookies');
  return data;
};

export const testCookiesFile = async () => {
  const { data } = await apiClient.post('/settings/cookies/test');
  return data;
};
