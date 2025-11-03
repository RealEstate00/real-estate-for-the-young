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

export interface ChatMessage {
  role: string;
  content: string;
}

export interface SourceInfo {
  title: string;
  address: string;
  district: string;
}

export interface ChatResponse {
  message: string;
  sources: SourceInfo[];
  title?: string; // 대화 제목 (mT5 요약)
}

export interface ChatRequest {
  messages: ChatMessage[];
  model_type: string;
}

export const chat = async (
  messages: ChatMessage[],
  model_type: string = "ollama",
  abortSignal?: AbortSignal
): Promise<ChatResponse> => {
  const response = await fetch(`${API_URL}/api/llm/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    signal: abortSignal,
    body: JSON.stringify({
      messages,
      model_type,
    }),
  });

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  return response.json();
};

export const ask = async (
  question: string,
  model_type: string = "ollama"
): Promise<ChatResponse> => {
  const response = await fetch(`${API_URL}/api/llm/ask`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      question,
      model_type,
      with_memory: false,
    }),
  });

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  return response.json();
};

export const askWithAgent = async (
  question: string,
  model_type: string = "ollama"
): Promise<ChatResponse> => {
  const response = await fetch(`${API_URL}/api/llm/ask-agent`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      question,
      model_type,
      with_memory: false,
    }),
  });

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  return response.json();
};

export const clearMemory = async (
  model_type: string = "ollama"
): Promise<void> => {
  const response = await fetch(`${API_URL}/api/llm/clear-memory`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      model_type,
    }),
  });

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }
};
