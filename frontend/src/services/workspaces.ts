import { api, type ApiResponse } from './client';

export interface Workspace {
  id: number;
  name: string;
  type: 'PERSONAL' | 'TEAM';
  role: 'OWNER' | 'MEMBER';
}

export interface CreateWorkspacePayload {
  name: string;
  type: 'PERSONAL' | 'TEAM';
}

export async function fetchMyWorkspaces() {
  const res = await api.get<ApiResponse<Workspace[]>>('/workspaces');
  return res.data.data;
}

export async function createWorkspace(payload: CreateWorkspacePayload) {
  const res = await api.post<ApiResponse<Workspace>>('/workspaces', payload);
  return res.data.data;
}
