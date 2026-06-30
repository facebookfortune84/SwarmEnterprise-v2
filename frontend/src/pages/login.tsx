import React, { useState, useEffect, useCallback, useRef } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { useAuth } from '@/hooks/useAuth'
import { useAuthStore } from '@/store/authStore'
import { toast } from '@/components/ui/Toast'
import { Input, Button } from '@/components/ui'
import { ApiError } from '@/services/ApiClient'

const LOCKOUT_ATTEMPTS = 5
const LOCKOUT_SECONDS = 60

export default function LoginPage() {
  const { login, isAuthenticated } = useAuth()
  const { token } = useAuthStore()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const redirect = searchParams.get('redirect') ?? '/dashboard'

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [errors, setErrors] = useState<{ email?: string; password?: string; form?: string }>({})
  const [attempts, setAttempts] = useState(0)
  const [lockoutEnd, setLockoutEnd] = useState<number | null>(null)
  const [countdown, setCountdown] = useState(0)
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null)

  // Redirect if already authenticated
  useEffect(() => {
    if (isAuthenticated() || token) navigate(redirect, { replace: true })
  }, [isAuthenticated, token, navigate, redirect])

  // Countdown timer
  useEffect(() => {
    if (!lockoutEnd) return
    const tick = () => {
      const remaining = Math.ceil((lockoutEnd - Date.now()) / 1000)
      if (remaining <= 0) {
        setLockoutEnd(null)
        setCountdown(0)
        setAttempts(0)
        if (timerRef.current) clearInterval(timerRef.current)
      } else {
        setCountdown(remaining)
      }
    }
    tick()
    timerRef.current = setInterval(tick, 1000)
    return () => {
      if (timerRef.current) clearInterval(timerRef.current)
    }
  }, [lockoutEnd])

  const isLocked = !!lockoutEnd && Date.now() < lockoutEnd

  const validate = useCallback(() => {
    const errs: typeof errors = {}
    if (!email) errs.email = 'Email is required'
    else if (!/\S+@\S+\.\S+/.test(email)) errs.email = 'Invalid email address'
    if (!password) errs.password = 'Password is required'
    return errs
  }, [email, password])

  const handleSubmit = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault()
      if (isLocked) return

      const errs = validate()
      if (Object.keys(errs).length > 0) {
        setErrors(errs)
        return
      }
      setErrors({})
      setLoading(true)

      try {
        await login(email, password)
        toast.success('Welcome back!')
        navigate(redirect, { replace: true })
      } catch (err) {
        const newAttempts = attempts + 1
        setAttempts(newAttempts)

        if (newAttempts >= LOCKOUT_ATTEMPTS) {
          setLockoutEnd(Date.now() + LOCKOUT_SECONDS * 1000)
          setErrors({ form: `Too many failed attempts. Locked for ${LOCKOUT_SECONDS}s.` })
        } else {
          const msg =
            err instanceof ApiError
              ? err.message
              : 'Login failed. Check your credentials.'
          setErrors({ form: msg })
        }
      } finally {
        setLoading(false)
      }
    },
    [isLocked, validate, login, email, password, attempts, navigate, redirect],
  )

  return (
    <div className="min-h-screen flex items-center justify-center bg-neutral-950 px-4">
      <div className="w-full max-w-md">
        <div className="rounded-2xl border border-neutral-700 bg-neutral-900 p-8 shadow-2xl">
          <div className="mb-8 text-center">
            <div className="text-3xl mb-2">⚡</div>
            <h1 className="text-2xl font-bold text-neutral-100">SwarmEnterprise</h1>
            <p className="mt-1 text-sm text-neutral-400">Sign in to your account</p>
          </div>

          <form onSubmit={(e) => { void handleSubmit(e) }} noValidate className="space-y-4">
            {errors.form && (
              <div
                role="alert"
                className="rounded-lg border border-danger-700 bg-danger-950 px-4 py-3 text-sm text-danger-300"
              >
                {errors.form}
                {isLocked && (
                  <span className="block font-mono mt-1">
                    Unlocks in {countdown}s
                  </span>
                )}
              </div>
            )}

            <Input
              label="Email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              error={errors.email}
              placeholder="you@example.com"
              autoComplete="email"
              disabled={isLocked}
              required
            />

            <Input
              label="Password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              error={errors.password}
              placeholder="••••••••"
              autoComplete="current-password"
              disabled={isLocked}
              required
            />

            <Button
              type="submit"
              className="w-full"
              loading={loading}
              disabled={isLocked}
            >
              {isLocked ? `Locked (${countdown}s)` : 'Sign in'}
            </Button>
          </form>

          <p className="mt-6 text-center text-sm text-neutral-500">
            Don&apos;t have an account?{' '}
            <Link to="/register" className="text-brand-400 hover:text-brand-300 font-medium">
              Register
            </Link>
          </p>
        </div>
      </div>
    </div>
  )
}
