import React, { useState, useCallback } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '@/hooks/useAuth'
import { toast } from '@/components/ui/Toast'
import { Input, Button } from '@/components/ui'
import { ApiError } from '@/services/ApiClient'

export default function RegisterPage() {
  const { register } = useAuth()
  const navigate = useNavigate()

  const [fullName, setFullName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [loading, setLoading] = useState(false)
  const [errors, setErrors] = useState<{
    fullName?: string
    email?: string
    password?: string
    confirm?: string
    form?: string
  }>({})

  const validate = useCallback(() => {
    const errs: typeof errors = {}
    if (!fullName.trim()) errs.fullName = 'Full name is required'
    else if (fullName.trim().length < 2) errs.fullName = 'Name must be at least 2 characters'
    if (!email) errs.email = 'Email is required'
    else if (!/\S+@\S+\.\S+/.test(email)) errs.email = 'Invalid email address'
    if (!password) errs.password = 'Password is required'
    else if (password.length < 8) errs.password = 'Password must be at least 8 characters'
    if (!confirm) errs.confirm = 'Please confirm your password'
    else if (confirm !== password) errs.confirm = 'Passwords do not match'
    return errs
  }, [fullName, email, password, confirm])

  const handleSubmit = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault()
      const errs = validate()
      if (Object.keys(errs).length > 0) {
        setErrors(errs)
        return
      }
      setErrors({})
      setLoading(true)

      try {
        await register(email, password, fullName.trim())
        toast.success('Account created! Welcome.')
        navigate('/dashboard', { replace: true })
      } catch (err) {
        const msg =
          err instanceof ApiError ? err.message : 'Registration failed. Please try again.'
        setErrors({ form: msg })
      } finally {
        setLoading(false)
      }
    },
    [validate, register, email, password, fullName, navigate],
  )

  return (
    <div className="min-h-screen flex items-center justify-center bg-neutral-950 px-4">
      <div className="w-full max-w-md">
        <div className="rounded-2xl border border-neutral-700 bg-neutral-900 p-8 shadow-2xl">
          <div className="mb-8 text-center">
            <div className="text-3xl mb-2">⚡</div>
            <h1 className="text-2xl font-bold text-neutral-100">Create Account</h1>
            <p className="mt-1 text-sm text-neutral-400">Join SwarmEnterprise</p>
          </div>

          <form onSubmit={(e) => { void handleSubmit(e) }} noValidate className="space-y-4">
            {errors.form && (
              <div
                role="alert"
                className="rounded-lg border border-danger-700 bg-danger-950 px-4 py-3 text-sm text-danger-300"
              >
                {errors.form}
              </div>
            )}

            <Input
              label="Full Name"
              type="text"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              error={errors.fullName}
              placeholder="Jane Smith"
              autoComplete="name"
              required
            />

            <Input
              label="Email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              error={errors.email}
              placeholder="you@example.com"
              autoComplete="email"
              required
            />

            <Input
              label="Password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              error={errors.password}
              helperText="At least 8 characters"
              autoComplete="new-password"
              required
            />

            <Input
              label="Confirm Password"
              type="password"
              value={confirm}
              onChange={(e) => setConfirm(e.target.value)}
              error={errors.confirm}
              autoComplete="new-password"
              required
            />

            <Button type="submit" className="w-full" loading={loading}>
              Create Account
            </Button>
          </form>

          <p className="mt-6 text-center text-sm text-neutral-500">
            Already have an account?{' '}
            <Link to="/login" className="text-brand-400 hover:text-brand-300 font-medium">
              Sign in
            </Link>
          </p>
        </div>
      </div>
    </div>
  )
}
