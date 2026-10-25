/**
 * Login page — JWT authentication form.
 *
 * On successful login stores the token and redirects to /dashboard.
 * Demo credentials are pre-filled for the seeded admin user.
 */

import { useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { login } from '@/api/auth'
import { useTheme } from '@/store/theme-context'
import { cn } from '@/lib/utils'
import { Zap, Eye, EyeOff, Loader2, Sun, Moon, Info, Mail } from 'lucide-react'
import { AboutModal, ContactModal } from '@/components/common/about-contact-modal'

export function LoginPage() {
  const navigate = useNavigate()
  const { theme, toggleTheme } = useTheme()
  const [email, setEmail] = useState('admin@demo.local')
  const [password, setPassword] = useState('admin123')
  const [showPassword, setShowPassword] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [aboutOpen, setAboutOpen] = useState(false)
  const [contactOpen, setContactOpen] = useState(false)

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setError(null)
    setLoading(true)
    try {
      await login(email, password)
      navigate('/dashboard', { replace: true })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Login failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="relative flex min-h-screen items-center justify-center bg-background p-4 transition-colors duration-200">
      {/* Light / Dark Mode Toggle Button */}
      <button
        id="login-theme-toggle"
        type="button"
        onClick={toggleTheme}
        className={cn(
          'fixed top-5 right-5 z-20 flex h-10 w-10 items-center justify-center rounded-xl',
          'border border-border/80 bg-card/90 shadow-md backdrop-blur-md',
          'text-foreground transition-all duration-200 hover:bg-accent hover:border-primary/40 focus-ring',
        )}
        aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
        title={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
      >
        {theme === 'dark' ? (
          <Sun className="h-5 w-5 text-amber-400 transition-transform hover:rotate-45" />
        ) : (
          <Moon className="h-5 w-5 text-indigo-600 transition-transform hover:-rotate-12" />
        )}
      </button>

      {/* Background gradient blobs */}
      <div className="pointer-events-none fixed inset-0 overflow-hidden">
        <div className="absolute -top-40 -right-40 h-96 w-96 rounded-full bg-primary/10 blur-3xl" />
        <div className="absolute -bottom-40 -left-40 h-96 w-96 rounded-full bg-purple-500/10 blur-3xl" />
      </div>

      <div className="w-full max-w-md animate-fade-in relative z-10">
        {/* Card */}
        <div className="glass rounded-2xl p-8 shadow-xl shadow-slate-900/5 dark:shadow-2xl dark:shadow-black/40 border border-border/80 dark:border-border/50">
          {/* Logo */}
          <div className="mb-8 text-center">
            <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-indigo-500 to-purple-600 shadow-lg shadow-indigo-500/30">
              <Zap className="h-8 w-8 text-white" />
            </div>
            <h1 className="text-2xl font-bold tracking-tight text-foreground">QuantiText</h1>
            <p className="mt-1 text-sm text-muted-foreground">
              AI-powered Business Intelligence
            </p>
          </div>

          {/* Error */}
          {error && (
            <div className="mb-4 rounded-lg border border-critical/30 bg-critical/10 px-4 py-3" role="alert">
              <p className="text-sm font-medium text-critical">{error}</p>
            </div>
          )}

          {/* Form */}
          <form onSubmit={handleSubmit} className="space-y-4" id="login-form">
            <div>
              <label htmlFor="email" className="block text-sm font-semibold text-foreground mb-1.5">
                Email
              </label>
              <input
                id="email"
                type="email"
                autoComplete="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className={cn(
                  'w-full rounded-lg border border-input bg-card px-3 py-2.5 text-sm text-foreground',
                  'placeholder:text-muted-foreground focus-ring transition-colors',
                  'focus:border-primary',
                )}
                placeholder="you@example.com"
              />
            </div>

            <div>
              <label htmlFor="password" className="block text-sm font-semibold text-foreground mb-1.5">
                Password
              </label>
              <div className="relative">
                <input
                  id="password"
                  type={showPassword ? 'text' : 'password'}
                  autoComplete="current-password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className={cn(
                    'w-full rounded-lg border border-input bg-card px-3 py-2.5 text-sm pr-10 text-foreground',
                    'placeholder:text-muted-foreground focus-ring transition-colors',
                    'focus:border-primary',
                  )}
                  placeholder="••••••••"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground focus-ring rounded p-1 transition-colors"
                  aria-label={showPassword ? 'Hide password' : 'Show password'}
                >
                  {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
            </div>

            <button
              id="login-submit"
              type="submit"
              disabled={loading}
              className={cn(
                'w-full rounded-lg bg-primary px-4 py-2.5 text-sm font-semibold text-primary-foreground',
                'transition-all duration-200 hover:opacity-90 active:scale-[0.98]',
                'focus-ring disabled:opacity-50 disabled:cursor-not-allowed',
                'shadow-lg shadow-primary/25',
              )}
            >
              {loading ? (
                <span className="flex items-center justify-center gap-2">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Signing in…
                </span>
              ) : (
                'Sign In'
              )}
            </button>
          </form>

          {/* Demo hint */}
          <div className="mt-6 rounded-lg bg-secondary/80 border border-border/70 px-4 py-3">
            <p className="text-xs text-muted-foreground text-center">
              <span className="font-semibold text-foreground">Demo credentials</span> are pre-filled.
              Run <code className="font-mono text-primary font-medium">python -m data.seed</code> to populate the database.
            </p>
          </div>
        </div>

        {/* Synthetic data disclaimer */}
        <p className="mt-4 text-center text-xs text-muted-foreground">
          ⚠️ This system uses <span className="font-medium text-foreground">synthetic data</span> for demonstration.
        </p>
      </div>

      {/* Bottom-left corner: Individual About & Contact Us options */}
      <div className="fixed bottom-5 left-5 z-20 flex items-center gap-2">
        <button
          id="login-about-btn"
          type="button"
          onClick={() => setAboutOpen(true)}
          className={cn(
            'flex items-center gap-1.5 rounded-xl border border-border/80 bg-card/90 px-3 py-1.5',
            'text-xs font-medium text-muted-foreground shadow-sm backdrop-blur-md',
            'transition-all duration-200 hover:text-foreground hover:bg-accent hover:border-primary/40 focus-ring',
          )}
          aria-label="About QuantiText"
        >
          <Info className="h-3.5 w-3.5 text-primary" />
          <span>About</span>
        </button>

        <button
          id="login-contact-btn"
          type="button"
          onClick={() => setContactOpen(true)}
          className={cn(
            'flex items-center gap-1.5 rounded-xl border border-border/80 bg-card/90 px-3 py-1.5',
            'text-xs font-medium text-muted-foreground shadow-sm backdrop-blur-md',
            'transition-all duration-200 hover:text-foreground hover:bg-accent hover:border-primary/40 focus-ring',
          )}
          aria-label="Contact Us"
        >
          <Mail className="h-3.5 w-3.5 text-primary" />
          <span>Contact Us</span>
        </button>
      </div>

      {/* Individual Modals */}
      <AboutModal isOpen={aboutOpen} onClose={() => setAboutOpen(false)} />
      <ContactModal isOpen={contactOpen} onClose={() => setContactOpen(false)} />
    </div>
  )
}
