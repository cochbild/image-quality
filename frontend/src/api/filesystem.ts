import apiClient from './client';

export interface Drive {
  path: string;
  label: string;
}

export interface FsEntry {
  name: string;
  path: string;
  type: 'directory' | 'image';
}

export interface BrowseResult {
  path: string;
  exists: boolean;
  is_dir?: boolean;
  parent: string;
  entries: FsEntry[];
  image_count?: number;
  error?: string;
}

export async function getDrives(): Promise<Drive[]> {
  const { data } = await apiClient.get('/filesystem/drives');
  return data.drives;
}

export async function browseDirectory(path: string): Promise<BrowseResult> {
  const { data } = await apiClient.get('/filesystem/browse', { params: { path } });
  return data;
}
