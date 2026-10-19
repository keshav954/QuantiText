/**
 * API client for Copilot NL2SQL chat endpoints.
 */

import { apiFetch } from './client'

export interface QueryResult {
  sql: string
  columns: string[]
  rows: unknown[][]
  row_count: number
  chart_type: string | null
}

export interface ChatResponse {
  session_id: string
  question: string
  answer: string
  sql: string | null
  result: QueryResult | null
  follow_up_suggestions: string[]
  from_cache: boolean
}

export interface ChatSession {
  id: string
  title: string | null
  created_at: string
  message_count: number
}

export interface ChatMessageItem {
  role: 'user' | 'assistant'
  content: string
  timestamp: string | null
}

export function sendChatMessage(params: {
  question: string
  session_id?: string | null
}): Promise<ChatResponse> {
  return apiFetch('/copilot/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
  })
}

export function fetchSessions(limit = 20): Promise<ChatSession[]> {
  return apiFetch(`/copilot/sessions?limit=${limit}`)
}

export function fetchSessionMessages(sessionId: string): Promise<ChatMessageItem[]> {
  return apiFetch(`/copilot/sessions/${sessionId}`)
}
