/**
 * 인증 관련 API 서비스
 */

const API_URL = (import.meta as any).env?.VITE_API_URL || "http://localhost:8000";

// ==================== Types ====================

export interface UserRegister {
  email: string;
  username: string;
  password: string;
  full_name?: string;
}

export interface UserLogin {
  email: string;
  password: string;
}

export interface User {
  id: number;
  email: string;
  username: string;
  full_name: string | null;
  is_active: boolean;
  is_verified: boolean;
  created_at: string;
  last_login_at: string | null;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  user: User;
}

// ==================== Local Storage ====================

const TOKEN_KEY = "auth_token";
const USER_KEY = "auth_user";

export const saveAuthData = (tokenResponse: TokenResponse) => {
  localStorage.setItem(TOKEN_KEY, tokenResponse.access_token);
  localStorage.setItem(USER_KEY, JSON.stringify(tokenResponse.user));
};

export const getToken = (): string | null => {
  return localStorage.getItem(TOKEN_KEY);
};

export const getUser = (): User | null => {
  const userStr = localStorage.getItem(USER_KEY);
  return userStr ? JSON.parse(userStr) : null;
};

export const clearAuthData = () => {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
};

export const isAuthenticated = (): boolean => {
  return !!getToken();
};

// ==================== API Functions ====================

/**
 * 회원가입
 */
export const register = async (
  userData: UserRegister
): Promise<TokenResponse> => {
  const response = await fetch(`${API_URL}/api/auth/register`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(userData),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Registration failed");
  }

  const tokenResponse: TokenResponse = await response.json();
  saveAuthData(tokenResponse);
  return tokenResponse;
};

/**
 * 로그인
 */
export const login = async (
  credentials: UserLogin
): Promise<TokenResponse> => {
  const response = await fetch(`${API_URL}/api/auth/login`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(credentials),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Login failed");
  }

  const tokenResponse: TokenResponse = await response.json();
  saveAuthData(tokenResponse);
  return tokenResponse;
};

/**
 * 로그아웃
 */
export const logout = () => {
  clearAuthData();
};

/**
 * 현재 사용자 정보 조회
 */
export const getCurrentUser = async (): Promise<User> => {
  const token = getToken();
  if (!token) {
    throw new Error("Not authenticated");
  }

  const response = await fetch(`${API_URL}/api/auth/me`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });

  if (!response.ok) {
    if (response.status === 401) {
      clearAuthData();
    }
    const error = await response.json();
    throw new Error(error.detail || "Failed to get user info");
  }

  return response.json();
};

/**
 * 인증된 요청을 위한 헤더 생성
 */
export const getAuthHeaders = (): HeadersInit => {
  const token = getToken();
  return {
    "Content-Type": "application/json",
    ...(token && { Authorization: `Bearer ${token}` }),
  };
};
