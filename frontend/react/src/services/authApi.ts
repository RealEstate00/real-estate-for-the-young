/**
 * 인증 관련 API 서비스
 */

const API_URL =
  (import.meta as any).env?.VITE_API_URL || "http://localhost:8000";

// ==================== Types ====================

export interface UserRegister {
  email: string;
  username: string;
  password: string;
  password_confirm: string;
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
  const response = await fetch(`${API_URL}/api/auth/register/`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(userData),
  });

  if (!response.ok) {
    const error = await response.json();

    // 필드별 에러 메시지 처리
    if (error.email) {
      const emailError = error.email[0];
      if (emailError.includes("이미 존재합니다") || emailError.includes("already exists")) {
        throw new Error("이메일: 이미 등록된 이메일입니다.");
      }
      throw new Error(`이메일: ${emailError}`);
    }
    if (error.username) {
      const usernameError = error.username[0];
      if (usernameError.includes("이미 존재합니다") || usernameError.includes("already exists")) {
        throw new Error("사용자명: 이미 사용 중인 사용자명입니다.");
      }
      throw new Error(`사용자명: ${usernameError}`);
    }
    if (error.password) {
      throw new Error(`비밀번호: ${error.password[0]}`);
    }
    if (error.password_confirm) {
      throw new Error(`비밀번호 확인: ${error.password_confirm[0]}`);
    }

    throw new Error(error.detail || "회원가입에 실패했습니다.");
  }

  const tokenResponse: TokenResponse = await response.json();
  saveAuthData(tokenResponse);
  return tokenResponse;
};

/**
 * 로그인
 */
export const login = async (credentials: UserLogin): Promise<TokenResponse> => {
  const response = await fetch(`${API_URL}/api/auth/login/`, {
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

  const response = await fetch(`${API_URL}/api/auth/me/`, {
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
