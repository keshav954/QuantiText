/**
 * useCopilotChat — encapsulates copilot chat state and TanStack mutation.
 *
 * Extracted from CopilotPage to keep the page focused on layout / UI
 * while making the chat logic testable and reusable.
 */

import { useState, useRef, useCallback } from 'react'
import { useMutation } from '@tanstack/react-query'
import { sendChatMessage, type ChatResponse, type QueryResult } from '@/api/copilot'

export interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
  sql?: string | null
  result?: QueryResult | null
  follow_up_suggestions?: string[]
}

export function useCopilotChat() {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [sessionId, setSessionId] = useState<string | null>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)

  const chatMutation = useMutation({
    mutationFn: (question: string) =>
      sendChatMessage({ question, session_id: sessionId }),
    onSuccess: (data: ChatResponse) => {
      setSessionId(data.session_id)
      const assistantMsg: Message = {
        id: data.message_id || crypto.randomUUID(),
        role: 'assistant',
        content: data.answer,
        timestamp: new Date(),
        sql: data.sql,
        result: data.result,
        follow_up_suggestions: data.follow_up_suggestions,
      }
      setMessages((prev) => [...prev, assistantMsg])
    },
    onError: (err: unknown) => {
      const errMsg: Message = {
        id: crypto.randomUUID(),
        role: 'assistant',
        content:
          err instanceof Error && err.message
            ? `Query issue: ${err.message}`
            : 'Something went wrong. Please try again.',
        timestamp: new Date(),
      }
      setMessages((prev) => [...prev, errMsg])
    },
  })

  const send = useCallback(
    (question: string = input.trim()) => {
      if (!question || chatMutation.isPending) return
      setInput('')

      const userMsg: Message = {
        id: crypto.randomUUID(),
        role: 'user',
        content: question,
        timestamp: new Date(),
      }
      setMessages((prev) => [...prev, userMsg])
      chatMutation.mutate(question)
    },
    [input, chatMutation],
  )

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault()
        send()
      }
    },
    [send],
  )

  const newChat = useCallback(() => {
    setMessages([])
    setSessionId(null)
    setInput('')
    inputRef.current?.focus()
  }, [])

  return {
    messages,
    input,
    setInput,
    sessionId,
    inputRef,
    isPending: chatMutation.isPending,
    send,
    handleKeyDown,
    newChat,
  }
}
