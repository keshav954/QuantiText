/**
 * Copilot page — NL2SQL chat interface with message history, query results, and charts.
 * Phase 7.
 */

import { useState } from 'react'
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts'
import {
  Bot,
  User,
  Send,
  Sparkles,
  Code2,
  Table,
  BarChart2,
  Plus,
} from 'lucide-react'
import { type QueryResult } from '@/api/copilot'
import { useAutoScroll } from '@/hooks/use-auto-scroll'
import { useCopilotChat, type Message } from '@/hooks/use-copilot-chat'

const CHART_COLORS = ['#6366f1', '#8b5cf6', '#a78bfa', '#34d399', '#fbbf24', '#f87171']

const STARTER_QUESTIONS = [
  'What is the total revenue for the last 30 days?',
  'Which 5 products have the highest revenue?',
  'Show me daily revenue trend for this month',
  'Which products are critically low on stock?',
  'What is the average order value by region?',
  'Show me the top 3 categories by sales volume',
]

function ResultChart({ result }: { result: QueryResult }) {
  if (!result.rows.length || result.chart_type === 'table') return null

  const colCount = result.columns.length
  if (colCount < 2) return null

  const valueCol = result.columns[1]

  const data = result.rows.slice(0, 20).map((row) => ({
    name: String(row[0]).substring(0, 20),
    value: typeof row[1] === 'number' ? row[1] : parseFloat(String(row[1])) || 0,
    ...Object.fromEntries(
      result.columns.slice(2).map((col, i) => [col, parseFloat(String(row[i + 2])) || 0])
    ),
  }))

  if (result.chart_type === 'pie') {
    return (
      <ResponsiveContainer width="100%" height={200}>
        <PieChart>
          <Pie data={data} dataKey="value" nameKey="name" outerRadius={80} label>
            {data.map((_, i) => (
              <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
            ))}
          </Pie>
          <Tooltip formatter={(v: number) => [v.toLocaleString(), valueCol]} />
          <Legend />
        </PieChart>
      </ResponsiveContainer>
    )
  }

  if (result.chart_type === 'line') {
    return (
      <ResponsiveContainer width="100%" height={200}>
        <LineChart data={data} margin={{ top: 5, right: 10, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
          <XAxis dataKey="name" tick={{ fontSize: 10, fill: '#6b7280' }} tickLine={false} axisLine={false} />
          <YAxis tick={{ fontSize: 10, fill: '#6b7280' }} tickLine={false} axisLine={false} />
          <Tooltip
            contentStyle={{
              background: 'hsl(var(--card))',
              border: '1px solid hsl(var(--border))',
              borderRadius: '8px',
              fontSize: '12px',
            }}
          />
          <Line type="monotone" dataKey="value" stroke="#6366f1" strokeWidth={2} dot={false} />
        </LineChart>
      </ResponsiveContainer>
    )
  }

  return (
    <ResponsiveContainer width="100%" height={200}>
      <BarChart data={data} margin={{ top: 5, right: 10, left: 0, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
        <XAxis dataKey="name" tick={{ fontSize: 10, fill: '#6b7280' }} tickLine={false} axisLine={false} />
        <YAxis tick={{ fontSize: 10, fill: '#6b7280' }} tickLine={false} axisLine={false} />
        <Tooltip
          contentStyle={{
            background: 'hsl(var(--card))',
            border: '1px solid hsl(var(--border))',
            borderRadius: '8px',
            fontSize: '12px',
          }}
        />
        <Bar dataKey="value" fill="#6366f1" radius={[4, 4, 0, 0]} maxBarSize={40} />
      </BarChart>
    </ResponsiveContainer>
  )
}

function ResultTable({ result }: { result: QueryResult }) {
  return (
    <div className="overflow-x-auto rounded-xl border border-border/50 mt-3">
      <table className="w-full text-xs">
        <thead className="bg-muted/30 border-b border-border">
          <tr>
            {result.columns.map((col) => (
              <th key={col} className="text-left px-3 py-2 text-muted-foreground font-medium">
                {col}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {result.rows.slice(0, 20).map((row, i) => (
            <tr key={i} className="border-b border-border/30 hover:bg-muted/20 transition-colors">
              {row.map((cell, j) => (
                <td key={j} className="px-3 py-2 text-foreground">
                  {String(cell)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      {result.row_count > 20 && (
        <p className="text-xs text-muted-foreground px-3 py-2">
          Showing 20 of {result.row_count} rows
        </p>
      )}
    </div>
  )
}

function MessageBubble({
  message,
  onFollowUp,
}: {
  message: Message
  onFollowUp: (q: string) => void
}) {
  const [showSql, setShowSql] = useState(false)
  const isUser = message.role === 'user'

  return (
    <div className={`flex gap-3 ${isUser ? 'justify-end' : 'justify-start'}`}>
      {!isUser && (
        <div className="shrink-0 w-8 h-8 bg-primary/20 rounded-xl flex items-center justify-center">
          <Bot className="h-4 w-4 text-primary" />
        </div>
      )}

      <div className={`max-w-[85%] space-y-2 ${isUser ? 'items-end' : 'items-start'} flex flex-col`}>
        <div
          className={`rounded-2xl px-4 py-3 ${
            isUser
              ? 'bg-primary text-primary-foreground rounded-tr-sm'
              : 'bg-card border border-border rounded-tl-sm'
          }`}
        >
          <p className="text-sm leading-relaxed whitespace-pre-wrap">{message.content}</p>
        </div>

        {/* SQL + result for assistant messages */}
        {!isUser && message.result && (
          <div className="w-full space-y-2">
            {/* Chart visualization */}
            {message.result.chart_type && message.result.chart_type !== 'table' && (
              <div className="bg-card border border-border rounded-2xl p-4">
                <div className="flex items-center gap-2 mb-3">
                  <BarChart2 className="h-3.5 w-3.5 text-muted-foreground" />
                  <span className="text-xs text-muted-foreground capitalize">
                    {message.result.chart_type} chart
                  </span>
                </div>
                <ResultChart result={message.result} />
              </div>
            )}

            {/* Data table */}
            <div className="bg-card border border-border rounded-2xl p-4">
              <div className="flex items-center justify-between mb-1">
                <div className="flex items-center gap-2">
                  <Table className="h-3.5 w-3.5 text-muted-foreground" />
                  <span className="text-xs text-muted-foreground">
                    {message.result.row_count} row{message.result.row_count !== 1 ? 's' : ''}
                  </span>
                </div>
                {message.sql && (
                  <button
                    onClick={() => setShowSql((v) => !v)}
                    className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors"
                  >
                    <Code2 className="h-3 w-3" />
                    {showSql ? 'Hide SQL' : 'Show SQL'}
                  </button>
                )}
              </div>
              {showSql && message.sql && (
                <pre className="bg-muted rounded-xl p-3 text-xs text-emerald-400 overflow-x-auto mb-2 font-mono">
                  {message.sql}
                </pre>
              )}
              <ResultTable result={message.result} />
            </div>
          </div>
        )}

        {/* Follow-up suggestions */}
        {!isUser && (message.follow_up_suggestions?.length ?? 0) > 0 && (
          <div className="flex flex-wrap gap-2">
            {message.follow_up_suggestions!.map((q) => (
              <button
                key={q}
                onClick={() => onFollowUp(q)}
                className="text-xs px-3 py-1.5 bg-muted hover:bg-muted/80 text-muted-foreground hover:text-foreground rounded-xl transition-all flex items-center gap-1 border border-border/50"
              >
                <Sparkles className="h-3 w-3" />
                {q}
              </button>
            ))}
          </div>
        )}

        <p className="text-xs text-muted-foreground px-1">
          {message.timestamp.toLocaleTimeString('en-GB', { timeStyle: 'short' })}
        </p>
      </div>

      {isUser && (
        <div className="shrink-0 w-8 h-8 bg-muted rounded-xl flex items-center justify-center">
          <User className="h-4 w-4 text-muted-foreground" />
        </div>
      )}
    </div>
  )
}

export function CopilotPage() {
  const {
    messages, input, setInput, inputRef,
    isPending, send: handleSend, handleKeyDown, newChat: handleNewChat,
  } = useCopilotChat()

  const messagesEndRef = useAutoScroll<HTMLDivElement>([messages])

  return (
    <div className="flex flex-col h-[calc(100vh-8rem)]">
      {/* Header */}
      <div className="flex items-center justify-between mb-4 shrink-0">
        <div>
          <h1 className="text-2xl font-bold text-foreground tracking-tight flex items-center gap-2">
            <Bot className="h-6 w-6 text-primary" />
            AI Chatbot
          </h1>
          <p className="text-muted-foreground text-sm mt-1">
            Ask questions in plain English · NL2SQL · Read-only · No PII sent to LLM
          </p>
        </div>
        <button
          id="new-chat-btn"
          onClick={handleNewChat}
          className="flex items-center gap-2 px-4 py-2 bg-muted hover:bg-muted/80 text-foreground rounded-xl text-sm font-medium transition-colors border border-border"
        >
          <Plus className="h-4 w-4" />
          New Chat
        </button>
      </div>

      {/* Messages area */}
      <div className="flex-1 overflow-y-auto space-y-4 pr-2 min-h-0">
        {messages.length === 0 ? (
          /* Welcome screen */
          <div className="flex flex-col items-center justify-center h-full text-center px-4">
            <div className="w-16 h-16 bg-primary/10 rounded-2xl flex items-center justify-center mb-4">
              <Bot className="h-8 w-8 text-primary" />
            </div>
            <h2 className="text-xl font-bold text-foreground mb-2">Ask anything about your data</h2>
            <p className="text-muted-foreground text-sm max-w-md mb-8">
              I'll convert your question to SQL, run it against the read-only database, and explain the results.
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 w-full max-w-2xl">
              {STARTER_QUESTIONS.map((q) => (
                <button
                  key={q}
                  id={`starter-${q.slice(0, 20).replace(/\s/g, '-')}`}
                  onClick={() => handleSend(q)}
                  className="text-left p-3 bg-card border border-border rounded-xl hover:border-primary/40 hover:bg-muted/50 transition-all group text-sm text-muted-foreground hover:text-foreground"
                >
                  <div className="flex items-start gap-2">
                    <Sparkles className="h-3.5 w-3.5 mt-0.5 text-primary shrink-0 opacity-60 group-hover:opacity-100" />
                    {q}
                  </div>
                </button>
              ))}
            </div>
          </div>
        ) : (
          <>
            {messages.map((msg) => (
              <MessageBubble
                key={msg.id}
                message={msg}
                onFollowUp={(q) => handleSend(q)}
              />
            ))}
            {isPending && (
              <div className="flex gap-3 justify-start">
                <div className="shrink-0 w-8 h-8 bg-primary/20 rounded-xl flex items-center justify-center">
                  <Bot className="h-4 w-4 text-primary animate-pulse" />
                </div>
                <div className="bg-card border border-border rounded-2xl rounded-tl-sm px-4 py-3">
                  <div className="flex gap-1 items-center h-5">
                    <span className="w-2 h-2 bg-primary/60 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                    <span className="w-2 h-2 bg-primary/60 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                    <span className="w-2 h-2 bg-primary/60 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                  </div>
                </div>
              </div>
            )}
          </>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input area */}
      <div className="shrink-0 mt-4">
        <div className="bg-card border border-border rounded-2xl p-3 flex items-end gap-3 focus-within:border-primary/50 transition-colors">
          <textarea
            ref={inputRef}
            id="copilot-input"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask a question about your data…"
            rows={1}
            className="flex-1 bg-transparent text-sm text-foreground placeholder:text-muted-foreground resize-none outline-none min-h-[24px] max-h-[120px] leading-6"
            style={{ height: 'auto' }}
            onInput={(e) => {
              const t = e.currentTarget
              t.style.height = 'auto'
              t.style.height = `${Math.min(t.scrollHeight, 120)}px`
            }}
          />
          <button
            id="send-btn"
            onClick={() => handleSend()}
            disabled={!input.trim() || isPending}
            className="shrink-0 w-9 h-9 bg-primary hover:bg-primary/90 disabled:opacity-40 text-primary-foreground rounded-xl flex items-center justify-center transition-all"
          >
            <Send className="h-4 w-4" />
          </button>
        </div>
        <p className="text-xs text-muted-foreground/60 mt-1.5 text-center">
          Only aggregated data · Read-only database · Press Enter to send
        </p>
      </div>
    </div>
  )
}
