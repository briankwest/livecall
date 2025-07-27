export interface User {
  id: string;
  email: string;
  username: string;
  full_name: string;
  is_active: boolean;
  is_admin: boolean;
}

export interface Call {
  id: string;
  signalwire_call_id: string;
  phone_number?: string;
  agent_id?: string;
  start_time: string;
  end_time?: string;
  duration_seconds?: number;
  status: 'active' | 'ended' | 'failed';
  listening_mode: 'agent' | 'customer' | 'both';
  direction: 'inbound' | 'outbound';
  transcription_count?: number;
  documents_accessed?: number;
}

export interface Transcription {
  id: string;
  speaker: 'agent' | 'customer';
  text: string;
  confidence?: number;
  timestamp: string;
  sentiment?: 'positive' | 'neutral' | 'negative';
  sentiment_score?: number;
}

export interface Document {
  document_id: string;
  title: string;
  content: string;
  similarity?: number;
  category?: string;
  meta_data?: Record<string, any>;
}

export interface AISuggestion {
  call_id: string;
  documents: Document[];
  summary: string;
  topics: string[];
}

export interface CallSummary {
  summary: string;
  key_topics: string[];
  sentiment_score: number;
  action_items: string[];
  metadata: Record<string, any>;
}

export interface WebSocketMessage {
  event: string;
  data: any;
}

export interface AuthToken {
  access_token: string;
  token_type: string;
}