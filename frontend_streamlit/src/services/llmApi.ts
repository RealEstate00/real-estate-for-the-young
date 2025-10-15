const API_URL =
  (import.meta as any).env?.VITE_API_URL || "http://localhost:8000";

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
}

export interface ChatRequest {
  messages: ChatMessage[];
  model_type: string;
}

export const chat = async (request: ChatRequest): Promise<ChatResponse> => {
  const response = await fetch(`${API_URL}/api/llm/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(request),
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
