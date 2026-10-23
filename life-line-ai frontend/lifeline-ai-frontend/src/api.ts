import axios from 'axios';

export const TOKEN_KEY = 'lifeline_token';
export const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000'
).replace(/\/$/, '');

export const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 15000,
  headers: { Accept: 'application/json' },
});

api.interceptors.request.use((config) => {
  const token = sessionStorage.getItem(TOKEN_KEY);
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error: unknown) => {
    if (axios.isAxiosError(error) && error.response?.status === 401) {
      sessionStorage.removeItem(TOKEN_KEY);
      window.dispatchEvent(new Event('lifeline:unauthorized'));
    }
    return Promise.reject(error);
  },
);

export type Role = 'reporter' | 'coordinator' | 'administrator';
export type Category =
  | 'road_hazard'
  | 'medical_assistance'
  | 'fire_environmental'
  | 'infrastructure_damage'
  | 'public_safety'
  | 'other';
export type IncidentStatus =
  | 'reported'
  | 'under_review'
  | 'assigned'
  | 'in_progress'
  | 'resolved'
  | 'closed';

export interface User {
  id: number;
  email: string;
  role: Role;
}

export interface Incident {
  id: number;
  title: string;
  description: string;
  category: Category;
  status: IncidentStatus;
  latitude: number | null;
  longitude: number | null;
  ai_summary: string;
  ai_confidence: number | null;
  ai_review_flag: boolean;
  reporter_id: number;
  assigned_to: number | null;
  created_at: string;
}

export interface IncidentNote {
  id: number;
  incident_id: number;
  author_id: number;
  content: string;
  created_at: string;
}

export interface IncidentAttachment {
  id: number;
  incident_id: number;
  uploader_id: number;
  original_filename: string;
  content_type: string;
  created_at: string;
}

export interface StatusHistoryEntry {
  old_status: string;
  new_status: string;
  actor_id: number;
  reason: string | null;
  created_at: string;
}

export interface DuplicateCandidate {
  incident_id: number;
  similarity: number;
  reason: string;
}

export interface Classification {
  category: Category;
  confidence: number | null;
  summary: string;
  indicators: string[];
  review_required: boolean;
  method: string;
  notice: string;
}

export interface DashboardSummary {
  total: number;
  open: number;
  resolved: number;
  requiring_human_review: number;
}

export interface DashboardLocation {
  id: number;
  title: string;
  latitude: number;
  longitude: number;
}

export interface DashboardTrend {
  date: string;
  count: number;
}

export const incidentStatuses: IncidentStatus[] = [
  'reported',
  'under_review',
  'assigned',
  'in_progress',
  'resolved',
  'closed',
];

export const categoryLabels: Record<Category, string> = {
  road_hazard: 'Road hazard',
  medical_assistance: 'Medical assistance',
  fire_environmental: 'Fire / environmental',
  infrastructure_damage: 'Infrastructure damage',
  public_safety: 'Public safety',
  other: 'Other',
};

export const statusLabels: Record<IncidentStatus, string> = {
  reported: 'Reported',
  under_review: 'Under review',
  assigned: 'Assigned',
  in_progress: 'In progress',
  resolved: 'Resolved',
  closed: 'Closed',
};

export const endpoints = {
  health: '/health',
  login: '/api/v1/auth/login',
  register: '/api/v1/auth/register',
  currentUser: '/api/v1/auth/me',
  classify: '/api/v1/ai/classify',
  incidents: '/api/v1/incidents',
  dashboardSummary: '/api/v1/dashboard/summary',
  dashboardCategories: '/api/v1/dashboard/categories',
  dashboardStatuses: '/api/v1/dashboard/statuses',
  dashboardLocations: '/api/v1/dashboard/locations',
  dashboardTrends: '/api/v1/dashboard/trends',
};

export async function login(username: string, password: string): Promise<string> {
  const body = new URLSearchParams({ username, password });
  const response = await api.post<{ access_token: string; token_type: string }>(
    endpoints.login,
    body,
    { headers: { 'Content-Type': 'application/x-www-form-urlencoded' } },
  );
  return response.data.access_token;
}

export async function register(
  email: string,
  password: string,
): Promise<User> {
  const response = await api.post<User>(endpoints.register, { email, password });
  return response.data;
}

export async function fetchCurrentUser(): Promise<User> {
  const response = await api.get<User>(endpoints.currentUser);
  return response.data;
}

export async function fetchIncidents(params: {
  page?: number;
  page_size?: number;
  category?: Category;
  status?: IncidentStatus;
} = {}): Promise<Incident[]> {
  const response = await api.get<Incident[]>(endpoints.incidents, { params });
  return response.data;
}

export async function createIncident(payload: {
  title: string;
  description: string;
  latitude?: number;
  longitude?: number;
}): Promise<Incident> {
  const response = await api.post<Incident>(endpoints.incidents, payload);
  return response.data;
}

export async function fetchIncident(id: number): Promise<Incident> {
  const response = await api.get<Incident>(`${endpoints.incidents}/${id}`);
  return response.data;
}

export async function updateIncident(
  id: number,
  payload: Partial<Pick<Incident, 'title' | 'description' | 'latitude' | 'longitude'>>,
): Promise<Incident> {
  const response = await api.patch<Incident>(
    `${endpoints.incidents}/${id}`,
    payload,
  );
  return response.data;
}

export async function fetchNotes(id: number): Promise<IncidentNote[]> {
  const response = await api.get<IncidentNote[]>(
    `${endpoints.incidents}/${id}/notes`,
  );
  return response.data;
}

export async function createNote(id: number, content: string): Promise<IncidentNote> {
  const response = await api.post<IncidentNote>(
    `${endpoints.incidents}/${id}/notes`,
    { content },
  );
  return response.data;
}

export async function fetchAttachments(id: number): Promise<IncidentAttachment[]> {
  const response = await api.get<IncidentAttachment[]>(
    `${endpoints.incidents}/${id}/attachments`,
  );
  return response.data;
}

export async function uploadAttachment(
  id: number,
  file: File,
): Promise<IncidentAttachment> {
  const body = new FormData();
  body.append('file', file);
  const response = await api.post<IncidentAttachment>(
    `${endpoints.incidents}/${id}/attachments`,
    body,
  );
  return response.data;
}

export async function downloadAttachment(
  incidentId: number,
  attachmentId: number,
): Promise<Blob> {
  const response = await api.get<Blob>(
    `${endpoints.incidents}/${incidentId}/attachments/${attachmentId}`,
    { responseType: 'blob' },
  );
  return response.data;
}

export async function changeIncidentStatus(
  id: number,
  status: IncidentStatus,
  reason: string,
): Promise<Incident> {
  const response = await api.post<Incident>(
    `${endpoints.incidents}/${id}/status`,
    { status, reason: reason || null },
  );
  return response.data;
}

export async function assignIncident(
  id: number,
  coordinator_id: number,
): Promise<Incident> {
  const response = await api.post<Incident>(
    `${endpoints.incidents}/${id}/assign`,
    { coordinator_id },
  );
  return response.data;
}

export async function fetchHistory(id: number): Promise<StatusHistoryEntry[]> {
  const response = await api.get<StatusHistoryEntry[]>(
    `${endpoints.incidents}/${id}/history`,
  );
  return response.data;
}

export async function fetchDuplicates(id: number): Promise<DuplicateCandidate[]> {
  const response = await api.get<DuplicateCandidate[]>(
    `${endpoints.incidents}/${id}/duplicates`,
  );
  return response.data;
}

export async function classifyIncident(description: string): Promise<Classification> {
  const response = await api.post<Classification>(endpoints.classify, { description });
  return response.data;
}

export function readableError(error: unknown): string {
  if (axios.isAxiosError(error)) {
    if (!error.response) {
      return 'Cannot reach the configured API. Check that FastAPI is running and VITE_API_BASE_URL is correct.';
    }
    const status = error.response.status;
    const data = error.response.data as { detail?: unknown } | undefined;
    if (status === 401) return 'Your session is invalid or expired. Please sign in again.';
    if (status === 403) return 'You do not have permission to perform this action.';
    if (typeof data?.detail === 'string') return data.detail;
    if (Array.isArray(data?.detail)) {
      return data.detail
        .map((item: { msg?: string; loc?: unknown[] }) =>
          `${(item.loc || []).join('.')}: ${item.msg || 'Invalid value'}`,
        )
        .join(' · ');
    }
    return `The API request failed (${status}).`;
  }
  return error instanceof Error ? error.message : 'Something went wrong.';
}
