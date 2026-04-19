import apiClient from './client';

export interface Root {
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
  parent: string | null;
  entries: FsEntry[];
  image_count?: number;
}

export async function getRoots(): Promise<Root[]> {
  const { data } = await apiClient.get('/filesystem/roots');
  return data.roots;
}

export async function browseDirectory(path: string): Promise<BrowseResult> {
  const { data } = await apiClient.get('/filesystem/browse', { params: { path } });
  return data;
}
