import { api, type ApiResponse } from './client';

export interface TokenResponse {
  accessToken: string;
  refreshToken: string;
}

export interface UserProfile {
  id: number;
  email: string;
  nickname: string;
  profileImageUrl: string | null;
  provider: 'LOCAL' | 'KAKAO' | 'GOOGLE';
  emailVerified: boolean;
  /**
   * 아바타 색 — 서버는 대문자로 준다("WHITE").
   * 이미지 매핑은 getSpacemanImage 가 대소문자를 맞춰 처리하므로 그대로 넘긴다.
   * 좁은 유니온 대신 string 인 이유: 서버가 새 색을 추가해도 화면이 깨지지 않아야 한다.
   */
  avatarColor: string;
  /**
   * 가입할 때 서버가 만들어준 개인 워크스페이스 id.
   * 클라이언트가 알 방법이 없어서 프로필에 실려 온다.
   */
  personalSpaceId: number;
}

export interface SignupPayload {
  email: string;
  password: string;
  nickname: string;
}

export interface LoginPayload {
  email: string;
  password: string;
}

export async function signup(payload: SignupPayload) {
  const res = await api.post<ApiResponse<UserProfile>>('/auth/signup', payload);
  return res.data.data;
}

export async function login(payload: LoginPayload) {
  const res = await api.post<ApiResponse<TokenResponse>>('/auth/login', payload);
  return res.data.data;
}

export async function logout() {
  await api.post<ApiResponse<null>>('/auth/logout');
}

export async function fetchMyProfile() {
  const res = await api.get<ApiResponse<UserProfile>>('/users/me');
  return res.data.data;
}
