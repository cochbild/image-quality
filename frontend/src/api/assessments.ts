import apiClient from './client';

export interface CategoryScore {
  category: string;
  score: number;
  reasoning: string | null;
  was_deep_dive: boolean;
}

export interface Assessment {
  id: number;
  scan_id: number;
  filename: string;
  file_path: string;
  destination_path: string | null;
  passed: boolean | null;
  triage_score: number | null;
  created_at: string;
  category_scores: CategoryScore[];
}

export interface Stats {
  total_assessed: number;
  passed: number;
  failed: number;
  pass_rate: number;
}

export async function getAssessmentsByScan(scanId: number, passed?: boolean): Promise<Assessment[]> {
  const params: Record<string, unknown> = {};
  if (passed !== undefined) params.passed = passed;
  const { data } = await apiClient.get(`/assessments/by-scan/${scanId}`, { params });
  return data;
}

export async function getAssessment(id: number): Promise<Assessment> {
  const { data } = await apiClient.get(`/assessments/${id}`);
  return data;
}

export async function getStats(): Promise<Stats> {
  const { data } = await apiClient.get('/assessments/stats/summary');
  return data;
}
