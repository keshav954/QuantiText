/**
 * Auth API — login, logout, and /me hooks.
 */

import { api } from '@/api/client'

export interface TokenResponse {
  access_token: string
  token_type: string
  expires_in: number
}

export interface UserMe {
  id: string
  org_id: string
  email: string
  full_name: string
  role: string
  is_active: boolean
  created_at: string
}

export async function login(email: string, password: string): Promise<TokenResponse> {
  const data = await api.post<TokenResponse>('/auth/login', { email, password })
  localStorage.setItem('quantitext-token', data.access_token)
  return data
}

export function logout(): void {
  localStorage.removeItem('quantitext-token')
  window.location.href = '/login'
}

export async function getMe(): Promise<UserMe> {
  return api.get<UserMe>('/auth/me')
}

export function getToken(): string | null {
  return localStorage.getItem('quantitext-token')
}
