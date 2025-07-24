import axios from 'axios';
import { AuthToken, User, Call, Transcription, Document, CallSummary } from '../types';

// Use relative URLs when accessing through a proxy (like ngrok)
const API_BASE_URL = (import.meta.env?.VITE_API_URL as string) || '';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add auth token to requests
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Handle auth errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('access_token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export const authService = {
  login: async (username: string, password: string): Promise<AuthToken> => {
    const formData = new FormData();
    formData.append('username', username);
    formData.append('password', password);
    
    const response = await api.post<AuthToken>('/api/auth/login', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    
    localStorage.setItem('access_token', response.data.access_token);
    return response.data;
  },
  
  register: async (data: {
    email: string;
    username: string;
    password: string;
    full_name: string;
  }): Promise<User> => {
    const response = await api.post<User>('/api/auth/register', data);
    return response.data;
  },
  
  getMe: async (): Promise<User> => {
    const response = await api.get<User>('/api/auth/me');
    return response.data;
  },
  
  logout: async (): Promise<void> => {
    await api.post('/api/auth/logout');
    localStorage.removeItem('access_token');
  },
};

export const callsService = {
  listCalls: async (params?: {
    skip?: number;
    limit?: number;
    status?: string;
    webrtc_call_id?: string;
  }): Promise<Call[]> => {
    const response = await api.get<Call[]>('/api/calls/', { params });
    return response.data;
  },
  
  getCall: async (callId: string): Promise<Call> => {
    const response = await api.get<Call>(`/api/calls/${callId}`);
    return response.data;
  },
  
  getTranscripts: async (callId: string): Promise<Transcription[]> => {
    const response = await api.get<Transcription[]>(`/api/calls/${callId}/transcripts`);
    return response.data;
  },
  
  getSummary: async (callId: string): Promise<CallSummary> => {
    const response = await api.get<CallSummary>(`/api/calls/${callId}/summary`);
    return response.data;
  },
  
  endCall: async (callId: string): Promise<{ status: string; summary: any }> => {
    const response = await api.post(`/api/calls/${callId}/end`);
    return response.data;
  },
  
  initiateCall: async (data: {
    to_number: string;
    agent_name: string;
    listening_mode: string;
    call_reason?: string;
    webrtc_call_id?: string;
    from_number?: string;
    direction?: 'inbound' | 'outbound';
  }): Promise<{
    call_id: string;
    signalwire_call_id: string;
    status: string;
    message: string;
  }> => {
    const response = await api.post('/api/calls/initiate', data);
    return response.data;
  },
};

export const documentsService = {
  listDocuments: async (category?: string): Promise<Document[]> => {
    const response = await api.get<Document[]>('/api/documents/', {
      params: category ? { category } : undefined,
    });
    return response.data;
  },
  
  getDocument: async (documentId: string): Promise<Document> => {
    const response = await api.get<Document>(`/api/documents/${documentId}`);
    return response.data;
  },
  
  searchDocuments: async (query: string, category?: string, limit = 5): Promise<Document[]> => {
    const response = await api.post<Document[]>('/api/documents/search', {
      query,
      category,
      limit,
    });
    return response.data;
  },
  
  createDocument: async (data: {
    document_id: string;
    title: string;
    content: string;
    category?: string;
    metadata?: Record<string, any>;
  }): Promise<{ status: string; document_id: string }> => {
    const response = await api.post('/api/documents/', data);
    return response.data;
  },
  
  deleteDocument: async (documentId: string): Promise<void> => {
    await api.delete(`/api/documents/${documentId}`);
  },
};

export const settingsService = {
  getSettings: async (): Promise<{
    listening_modes: string[];
    features: Record<string, boolean>;
  }> => {
    const response = await api.get('/api/settings');
    return response.data;
  },
};

export { api };
export default api;