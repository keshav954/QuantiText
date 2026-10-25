/**
 * Individual About and Contact Us Modals.
 * Rendered via React Portal into document.body to prevent any parent container
 * (such as sidebar backdrop-filter or transforms) from constraining or clipping the modal.
 */

import { useEffect, useState, type FormEvent } from 'react'
import { createPortal } from 'react-dom'
import {
  X,
  Zap,
  Mail,
  CheckCircle2,
  Send,
  Sparkles,
  Layers,
  Database,
  Brain,
  MessageSquare,
} from 'lucide-react'

interface ModalProps {
  isOpen: boolean
  onClose: () => void
}

/**
 * Individual About Modal
 */
export function AboutModal({ isOpen, onClose }: ModalProps) {
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === 'Escape') onClose()
    }
    if (isOpen) {
      window.addEventListener('keydown', handleKeyDown)
    }
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [isOpen, onClose])

  if (!isOpen || typeof document === 'undefined') return null

  const modalContent = (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-fade-in"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-labelledby="about-modal-title"
    >
      <div
        className="w-full max-w-lg max-h-[90vh] overflow-y-auto overflow-x-hidden rounded-2xl border border-border/80 bg-card p-6 shadow-2xl shadow-black/40 space-y-5 text-foreground relative animate-scale-in"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header with Title & prominent X button */}
        <div className="flex items-center justify-between border-b border-border/80 pb-4">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 shadow-md shadow-indigo-500/25">
              <Zap className="h-5 w-5 text-white" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 id="about-modal-title" className="text-lg font-bold tracking-tight text-foreground">
                  About QuantiText
                </h2>
                <span className="rounded-full bg-primary/10 px-2 py-0.5 text-[11px] font-semibold text-primary">
                  v0.1.0
                </span>
              </div>
              <p className="text-xs text-muted-foreground mt-0.5">
                AI-Powered Business Intelligence & Decision Support
              </p>
            </div>
          </div>

          <button
            id="about-modal-close"
            type="button"
            onClick={onClose}
            className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl border border-border/80 bg-muted/40 text-muted-foreground hover:bg-accent hover:text-foreground hover:border-primary/40 transition-colors focus-ring"
            aria-label="Close About dialog"
            title="Close dialog"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Overview text */}
        <p className="text-xs text-muted-foreground leading-relaxed">
          QuantiText unifies forecasting, anomaly detection, NL2SQL chat, and automated executive reporting into a single closed-loop business intelligence workflow:
        </p>

        {/* Closed-Loop Architecture */}
        <div className="rounded-xl border border-border/80 bg-secondary/60 p-3.5 space-y-2">
          <p className="text-[11px] font-semibold uppercase tracking-wider text-primary">
            Closed-Loop Decision Architecture
          </p>
          <div className="flex flex-wrap items-center gap-1.5 text-xs text-foreground">
            <span className="rounded-md bg-card px-2.5 py-1 border border-border font-medium">Anomaly</span>
            <span className="text-muted-foreground font-bold">→</span>
            <span className="rounded-md bg-card px-2.5 py-1 border border-border font-medium">Root Cause</span>
            <span className="text-muted-foreground font-bold">→</span>
            <span className="rounded-md bg-card px-2.5 py-1 border border-border font-medium">Forecast Impact</span>
            <span className="text-muted-foreground font-bold">→</span>
            <span className="rounded-md bg-card px-2.5 py-1 border border-border font-medium">Recommendation</span>
            <span className="text-muted-foreground font-bold">→</span>
            <span className="rounded-md bg-card px-2.5 py-1 border border-border font-medium">Human Approval</span>
          </div>
        </div>

        {/* Feature Cards Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
          <div className="rounded-xl border border-border/70 bg-card p-3 space-y-1">
            <div className="flex items-center gap-2 text-xs font-semibold text-foreground">
              <Brain className="h-4 w-4 text-primary shrink-0" />
              <span>AI Copilot & NL2SQL</span>
            </div>
            <p className="text-[11px] text-muted-foreground">
              Natural language database queries with automated charting and insights.
            </p>
          </div>

          <div className="rounded-xl border border-border/70 bg-card p-3 space-y-1">
            <div className="flex items-center gap-2 text-xs font-semibold text-foreground">
              <Layers className="h-4 w-4 text-purple-500 shrink-0" />
              <span>Demand Forecasting</span>
            </div>
            <p className="text-[11px] text-muted-foreground">
              LightGBM predictive algorithms with confidence bounds and MAPE metrics.
            </p>
          </div>

          <div className="rounded-xl border border-border/70 bg-card p-3 space-y-1">
            <div className="flex items-center gap-2 text-xs font-semibold text-foreground">
              <Database className="h-4 w-4 text-emerald-500 shrink-0" />
              <span>Inventory Analytics</span>
            </div>
            <p className="text-[11px] text-muted-foreground">
              Reorder-point modeling, stockout probability, and inventory velocity.
            </p>
          </div>

          <div className="rounded-xl border border-border/70 bg-card p-3 space-y-1">
            <div className="flex items-center gap-2 text-xs font-semibold text-foreground">
              <Sparkles className="h-4 w-4 text-amber-500 shrink-0" />
              <span>Executive Reporting</span>
            </div>
            <p className="text-[11px] text-muted-foreground">
              Automated briefing digests with key findings and export capabilities.
            </p>
          </div>
        </div>

        {/* Synthetic Data Transparency */}
        <div className="rounded-lg bg-warning/10 border border-warning/20 px-3 py-2 text-[11px] text-muted-foreground">
          ⚠️ <span className="font-semibold text-foreground">Data Transparency:</span> Inventory, lead-time, and cost metrics use synthetic data for demonstration.
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between pt-2 border-t border-border/60 text-xs">
          <span className="text-muted-foreground">Final-Year B.Tech Capstone Project</span>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg border border-border/80 bg-secondary/80 px-4 py-2 font-medium text-foreground hover:bg-accent transition-colors focus-ring"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  )

  return createPortal(modalContent, document.body)
}

/**
 * Individual Contact Us Modal
 */
export function ContactModal({ isOpen, onClose }: ModalProps) {
  const [submitted, setSubmitted] = useState(false)
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [message, setMessage] = useState('')

  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === 'Escape') onClose()
    }
    if (isOpen) {
      window.addEventListener('keydown', handleKeyDown)
      setSubmitted(false)
    }
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [isOpen, onClose])

  if (!isOpen || typeof document === 'undefined') return null

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault()
    setSubmitted(true)
  }

  const modalContent = (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-fade-in"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-labelledby="contact-modal-title"
    >
      <div
        className="w-full max-w-lg max-h-[90vh] overflow-y-auto overflow-x-hidden rounded-2xl border border-border/80 bg-card p-6 shadow-2xl shadow-black/40 space-y-5 text-foreground relative animate-scale-in"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header with Title & prominent X button */}
        <div className="flex items-center justify-between border-b border-border/80 pb-4">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-primary">
              <Mail className="h-5 w-5" />
            </div>
            <div>
              <h2 id="contact-modal-title" className="text-lg font-bold tracking-tight text-foreground">
                Contact Us
              </h2>
              <p className="text-xs text-muted-foreground mt-0.5">
                Have questions or feedback about QuantiText?
              </p>
            </div>
          </div>

          <button
            id="contact-modal-close"
            type="button"
            onClick={onClose}
            className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl border border-border/80 bg-muted/40 text-muted-foreground hover:bg-accent hover:text-foreground hover:border-primary/40 transition-colors focus-ring"
            aria-label="Close Contact dialog"
            title="Close dialog"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {submitted ? (
          <div className="rounded-xl border border-healthy/30 bg-healthy/10 p-6 text-center space-y-3 animate-fade-in">
            <CheckCircle2 className="h-10 w-10 text-healthy mx-auto" />
            <h3 className="text-sm font-bold text-foreground">Message Sent Successfully!</h3>
            <p className="text-xs text-muted-foreground max-w-sm mx-auto">
              Thank you for reaching out. We have logged your feedback and will review it promptly.
            </p>
            <div className="pt-2">
              <button
                type="button"
                onClick={() => {
                  setSubmitted(false)
                  setMessage('')
                }}
                className="text-xs font-semibold text-primary hover:underline"
              >
                Send another message
              </button>
            </div>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-3.5" id="contact-form">
            <div>
              <label htmlFor="contact-name" className="block text-xs font-semibold text-foreground mb-1">
                Your Name
              </label>
              <input
                id="contact-name"
                type="text"
                required
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Parth / Demo User"
                className="w-full rounded-lg border border-input bg-background px-3 py-2 text-xs text-foreground placeholder:text-muted-foreground focus-ring transition-colors focus:border-primary"
              />
            </div>

            <div>
              <label htmlFor="contact-email" className="block text-xs font-semibold text-foreground mb-1">
                Email Address
              </label>
              <input
                id="contact-email"
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="parth@example.com"
                className="w-full rounded-lg border border-input bg-background px-3 py-2 text-xs text-foreground placeholder:text-muted-foreground focus-ring transition-colors focus:border-primary"
              />
            </div>

            <div>
              <label htmlFor="contact-message" className="block text-xs font-semibold text-foreground mb-1">
                Message or Feedback
              </label>
              <textarea
                id="contact-message"
                required
                rows={3}
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                placeholder="Share your thoughts, suggestions, or bug reports…"
                className="w-full rounded-lg border border-input bg-background px-3 py-2 text-xs text-foreground placeholder:text-muted-foreground focus-ring transition-colors focus:border-primary resize-none"
              />
            </div>

            <button
              type="submit"
              id="contact-submit-btn"
              className="w-full flex items-center justify-center gap-2 rounded-lg bg-primary px-4 py-2 text-xs font-semibold text-primary-foreground shadow-md transition-all hover:opacity-90 active:scale-[0.99] focus-ring"
            >
              <Send className="h-3.5 w-3.5" />
              Send Feedback
            </button>
          </form>
        )}

        {/* Contact info channels */}
        <div className="pt-2 border-t border-border/60 grid grid-cols-2 gap-2 text-xs">
          <div className="rounded-lg bg-secondary/50 p-2.5">
            <p className="font-semibold text-foreground flex items-center gap-1.5">
              <Mail className="h-3.5 w-3.5 text-primary" />
              Direct Email
            </p>
            <p className="text-[11px] text-muted-foreground mt-0.5 font-mono">
              support@quantitext.local
            </p>
          </div>

          <div className="rounded-lg bg-secondary/50 p-2.5">
            <p className="font-semibold text-foreground flex items-center gap-1.5">
              <MessageSquare className="h-3.5 w-3.5 text-primary" />
              Project Docs
            </p>
            <p className="text-[11px] text-muted-foreground mt-0.5">
              Available under /docs
            </p>
          </div>
        </div>
      </div>
    </div>
  )

  return createPortal(modalContent, document.body)
}
