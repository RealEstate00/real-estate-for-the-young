// API URL 자동 감지: 현재 호스트 기반으로 설정
const getApiUrl = (): string => {
  // 환경 변수에서 명시적으로 설정된 경우 사용
  const envApiUrl = (import.meta as any).env?.VITE_API_URL;
  if (envApiUrl) {
    return envApiUrl;
  }

  // 현재 호스트 기반으로 API URL 자동 생성
  const hostname = window.location.hostname;
  const protocol = window.location.protocol;

  // localhost인 경우 기본 포트 사용
  if (hostname === "localhost" || hostname === "127.0.0.1") {
    return "http://localhost:8000";
  }

  // 네트워크 주소(IP 주소)인 경우 같은 호스트, 포트 8000 사용
  return `${protocol}//${hostname}:8000`;
};

const API_URL = getApiUrl();

// Helper function to get auth token
const getAuthToken = (): string | null => {
  return localStorage.getItem("auth_token");
};

// Helper function to create auth headers
const getAuthHeaders = (): HeadersInit => {
  const token = getAuthToken();
  const headers: HeadersInit = {
    "Content-Type": "application/json",
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  return headers;
};

export interface Message {
  id?: number;
  role: string;
  content: string;
  created_at?: string;
}

export interface Conversation {
  id: number;
  title: string;
  created_at: string;
  updated_at: string;
  messages?: Message[];
}

export interface ChatWithSaveRequest {
  conversation_id?: number | null;
  message: string;
  model_type?: string;
}

export interface ChatWithSaveResponse {
  conversation_id: number;
  user_message: Message;
  assistant_message: Message;
  sources: any[];
  title?: string;  // Generated title for first message
}

// Get all conversations for current user
export const getConversations = async (): Promise<Conversation[]> => {
  const response = await fetch(`${API_URL}/api/conversations/`, {
    method: "GET",
    headers: getAuthHeaders(),
  });

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  return response.json();
};

// Get single conversation with messages
export const getConversation = async (id: number): Promise<Conversation> => {
  const response = await fetch(`${API_URL}/api/conversations/${id}/`, {
    method: "GET",
    headers: getAuthHeaders(),
  });

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  return response.json();
};

// Create new conversation
export const createConversation = async (
  title: string
): Promise<Conversation> => {
  const response = await fetch(`${API_URL}/api/conversations/`, {
    method: "POST",
    headers: getAuthHeaders(),
    body: JSON.stringify({ title }),
  });

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  return response.json();
};

// Delete conversation
export const deleteConversation = async (id: number): Promise<void> => {
  const response = await fetch(`${API_URL}/api/conversations/${id}/`, {
    method: "DELETE",
    headers: getAuthHeaders(),
  });

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }
};

// Update conversation title
export const updateConversation = async (
  id: number,
  title: string
): Promise<Conversation> => {
  const response = await fetch(`${API_URL}/api/conversations/${id}/`, {
    method: "PATCH",
    headers: getAuthHeaders(),
    body: JSON.stringify({ title }),
  });

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  return response.json();
};

// Chat with LLM and save to database
// This is the main endpoint that combines LLM chat + DB save
export const chatWithSave = async (
  request: ChatWithSaveRequest
): Promise<ChatWithSaveResponse> => {
  const response = await fetch(`${API_URL}/api/conversations/chat/`, {
    method: "POST",
    headers: getAuthHeaders(),
    body: JSON.stringify({
      conversation_id: request.conversation_id,
      message: request.message,
      model_type: request.model_type || "ollama",
    }),
  });

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  return response.json();
};

// Check if user is authenticated
export const isAuthenticated = (): boolean => {
  return getAuthToken() !== null;
};
