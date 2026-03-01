import apiClient from './client';

export async function getAllSettings(): Promise<Record<string, string>> {
  const { data } = await apiClient.get('/settings/');
  return data;
}

export async function getSetting(key: string): Promise<string | null> {
  const { data } = await apiClient.get(`/settings/${key}`);
  return data.value;
}

export async function updateSetting(key: string, value: string): Promise<void> {
  await apiClient.put(`/settings/${key}`, { value });
}

export interface LMStudioStatus {
  connected: boolean;
  url: string;
}

export interface LMStudioModel {
  id: string;
  object: string;
}

export async function getLMStudioStatus(): Promise<LMStudioStatus> {
  const { data } = await apiClient.get('/lm-studio/status');
  return data;
}

export async function getLMStudioModels(): Promise<LMStudioModel[]> {
  const { data } = await apiClient.get('/lm-studio/models');
  return data.models || [];
}
