import apiClient from './client';

export interface Scan {
  id: number;
  input_dir: string;
  output_dir: string;
  reject_dir: string;
  started_at: string;
  completed_at: string | null;
  total_images: number;
  passed_count: number;
  failed_count: number;
  status: string;
}

export async function startScan(dirs?: { input_dir?: string; output_dir?: string; reject_dir?: string }): Promise<Scan> {
  const { data } = await apiClient.post('/scans/', dirs || {});
  return data;
}

export async function getScans(limit = 20): Promise<Scan[]> {
  const { data } = await apiClient.get('/scans/', { params: { limit } });
  return data;
}

export async function getScan(scanId: number): Promise<Scan> {
  const { data } = await apiClient.get(`/scans/${scanId}`);
  return data;
}

export async function cancelScan(scanId: number): Promise<void> {
  await apiClient.post(`/scans/${scanId}/cancel`);
}
