/**
 * Login page — JWT authentication form.
 *
 * On successful login stores the token and redirects to /dashboard.
 * Demo credentials are pre-filled for the seeded admin user.
 */

import { useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { login } from '@/api/auth'
import { cn } from '@/lib/utils'
import { Zap, Eye, EyeOff, Loader2 } from 'lucide-react'

export function LoginPage() {
  const navigate = useNavigate()
  const [email, setEmail] = useState('admin@demo.local')
  const [password, setPassword] = useState('admin123')
  const [showPassword, setShowPassword] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

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
    <div className="flex min-h-screen items-center justify-center bg-background p-4">
      {/* Background gradient blobs */}
      <div className="pointer-events-none fixed inset-0 overflow-hidden">
        <div className="absolute -top-40 -right-40 h-96 w-96 rounded-full bg-primary/10 blur-3xl" />
        <div className="absolute -bottom-40 -left-40 h-96 w-96 rounded-full bg-purple-500/10 blur-3xl" />
      </div>

      <div className="w-full max-w-md animate-fade-in">
        {/* Card */}
        <div className="glass rounded-2xl p-8 shadow-2xl shadow-black/20">
          {/* Logo */}
          <div className="mb-8 text-center">
            <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-indigo-500 to-purple-600 shadow-lg shadow-indigo-500/30">
              <Zap className="h-8 w-8 text-white" />
            </div>
            <h1 className="text-2xl font-bold text-foreground">QuantiText</h1>
            <p className="mt-1 text-sm text-muted-foreground">
              AI-powered Business Intelligence
            </p>
          </div>

          {/* Error */}
          {error && (
            <div className="mb-4 rounded-lg border border-critical/30 bg-critical/10 px-4 py-3" role="alert">
              <p className="text-sm text-critical">{error}</p>
            </div>
          )}

          {/* Form */}
          <form onSubmit={handleSubmit} className="space-y-4" id="login-form">
            <div>
              <label htmlFor="email" className="block text-sm font-medium text-foreground mb-1.5">
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
                  'w-full rounded-lg border border-input bg-background px-3 py-2.5 text-sm',
                  'placeholder:text-muted-foreground focus-ring transition-colors',
                  'focus:border-primary/50',
                )}
                placeholder="you@example.com"
              />
            </div>

            <div>
              <label htmlFor="password" className="block text-sm font-medium text-foreground mb-1.5">
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
                    'w-full rounded-lg border border-input bg-background px-3 py-2.5 text-sm pr-10',
                    'placeholder:text-muted-foreground focus-ring transition-colors',
                    'focus:border-primary/50',
                  )}
                  placeholder="••••••••"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground focus-ring rounded"
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
          <div className="mt-6 rounded-lg bg-secondary/50 px-4 py-3">
            <p className="text-xs text-muted-foreground text-center">
              <span className="font-medium text-foreground">Demo credentials</span> are pre-filled.
              Run <code className="font-mono text-primary">python -m data.seed</code> to populate the database.
            </p>
          </div>
        </div>

        {/* Synthetic data disclaimer */}
        <p className="mt-4 text-center text-xs text-muted-foreground">
          ⚠️ This system uses <span className="font-medium">synthetic data</span> for demonstration.
        </p>
      </div>
    </div>
  )
}
