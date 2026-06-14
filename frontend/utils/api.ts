import axios from 'axios';

// ─── Base URL ─────────────────────────────────────────────────────────────────
// Points to your friend's FastAPI backend (backend/main.py)
// Change this to the deployed Railway/Render URL when deployed
const BASE_URL = process.env.EXPO_PUBLIC_API_URL ?? 'http://127.0.0.1:8000';
// Note: Use 10.0.2.2 for Android emulator, or your laptop's IP for real device
// e.g. 'http://192.168.x.x:8000' — run `ipconfig` on Windows to find your IP

const api = axios.create({
  baseURL: BASE_URL,
  timeout: 30000, // 30s — AI responses can be slow
  headers: { 'Content-Type': 'application/json' },
});

// ─── Types matching backend/models/schemas.py exactly ────────────────────────

export interface Citation {
  case_name: string;
  court: string;
  year: string;
  section?: string;
}

export interface QueryRequest {
  query_text: string;
  language: string;       // 'urdu' | 'english' | 'roman_urdu'
  input_type: string;     // 'text' | 'voice'
}

export interface QueryResponse {
  answer: string;
  citations: Citation[];
  legal_domain: string;
  language_detected: string;
}

export interface FIRSection {
  section_number: string;
  title: string;
  min_punishment: string;
  max_punishment: string;
  bailable: boolean;
  explanation: string;
}

export interface FIRAnalysisResponse {
  sections: FIRSection[];
  plain_explanation: string;
  flags: string[];
  is_bailable: boolean;
}

export interface RiskFlag {
  clause_text: string;
  risk_level: string;   // 'HIGH' | 'MEDIUM' | 'LOW'
  explanation: string;
}

export interface DocumentAnalysisResponse {
  document_type: string;
  risk_flags: RiskFlag[];
  plain_explanation: string;
}

export interface TranscriptResponse {
  transcript: string;
  language: string;
}

export interface VoiceQueryResponse {
  transcript: string;
  language: string;
  legal_answer: QueryResponse;
}

// ─── API calls matching backend/routers/ ─────────────────────────────────────

// routers/query.py → POST /query/ask
export const askLegalQuery = async (payload: QueryRequest): Promise<QueryResponse> => {
  const res = await api.post('/query/ask', payload);
  return res.data;
};

// routers/query.py → GET /query/history/:userId
export const getQueryHistory = async (userId: string): Promise<QueryResponse[]> => {
  const res = await api.get(`/query/history/${userId}`);
  return res.data;
};

// routers/fir.py → POST /fir/analyze-image (multipart)
// routers/fir.py → POST /fir/analyze-image (multipart)
export const analyzeFIRImage = async (imageUri: string): Promise<FIRAnalysisResponse> => {
  const formData = new FormData();

  // Web browser: fetch the blob and append as File
  if (imageUri.startsWith('blob:') || imageUri.startsWith('http')) {
    const response = await fetch(imageUri);
    const blob = await response.blob();
    const file = new File([blob], 'fir.jpg', { type: 'image/jpeg' });
    formData.append('image', file);
  } else {
    // React Native mobile: use uri object format
    formData.append('image', {
      uri: imageUri,
      name: 'fir.jpg',
      type: 'image/jpeg',
    } as any);
  }

  const res = await api.post('/fir/analyze-image', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return res.data;
};

// routers/fir.py → POST /fir/analyze-text
export const analyzeFIRText = async (text: string): Promise<FIRAnalysisResponse> => {
  const res = await api.post('/fir/analyze-text', { text });
  return res.data;
};

// routers/document.py → POST /document/analyze (multipart)
// routers/document.py → POST /document/analyze (multipart)
export const analyzeDocument = async (imageUri: string): Promise<DocumentAnalysisResponse> => {
  const formData = new FormData();

  if (imageUri.startsWith('blob:') || imageUri.startsWith('http')) {
    const response = await fetch(imageUri);
    const blob = await response.blob();
    const file = new File([blob], 'document.jpg', { type: 'image/jpeg' });
    formData.append('image', file);
  } else {
    formData.append('image', {
      uri: imageUri,
      name: 'document.jpg',
      type: 'image/jpeg',
    } as any);
  }

  const res = await api.post('/document/analyze', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return res.data;
};

// routers/voice.py → POST /voice/transcribe-only (show transcript before sending)
export const transcribeAudio = async (audioUri: string): Promise<TranscriptResponse> => {
  const formData = new FormData();
  formData.append('audio', {
    uri: audioUri,
    name: 'voice.m4a',
    type: 'audio/m4a',
  } as any);
  const res = await api.post('/voice/transcribe-only', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return res.data;
};

// routers/voice.py → POST /voice/transcribe (transcribe + run RAG)
export const transcribeAndAsk = async (audioUri: string): Promise<VoiceQueryResponse> => {
  const formData = new FormData();
  formData.append('audio', {
    uri: audioUri,
    name: 'voice.m4a',
    type: 'audio/m4a',
  } as any);
  const res = await api.post('/voice/transcribe', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return res.data;
};

// Health check → GET /health
export const checkHealth = async (): Promise<boolean> => {
  try {
    const res = await api.get('/health');
    return res.data?.status === 'ok';
  } catch {
    return false;
  }
};

export default api;
