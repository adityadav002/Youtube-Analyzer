import { apiClient } from '../client';

export const getJobs = async (params) => {
  const { data } = await apiClient.get('/jobs', { params });
  return data;
};

export const cancelJob = async (id) => {
  const { data } = await apiClient.post(`/jobs/${id}/cancel`);
  return data;
};

export const retryJob = async (id) => {
  const { data } = await apiClient.post(`/jobs/${id}/retry`);
  return data;
};

export const getJobStatus = async (id) => {
  const { data } = await apiClient.get(`/jobs/${id}`);
  return data;
};
