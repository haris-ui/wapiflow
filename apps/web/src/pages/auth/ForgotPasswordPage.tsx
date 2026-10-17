import React, { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Link } from 'react-router-dom'
import { Mail, CheckCircle2, AlertCircle, ArrowLeft } from 'lucide-react'
import { useAuth } from '@/hooks/useAuth'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Label } from '@/components/ui/Label'

const forgotSchema = z.object({
  email: z.string().email('Please enter a valid email address'),
})

type ForgotFormValues = z.infer<typeof forgotSchema>

export const ForgotPasswordPage: React.FC = () => {
  const { resetPassword } = useAuth()
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [isSuccess, setIsSuccess] = useState<boolean>(false)

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<ForgotFormValues>({
    resolver: zodResolver(forgotSchema),
    defaultValues: { email: '' },
  })

  const onSubmit = async (values: ForgotFormValues) => {
    try {
      setErrorMessage(null)
      await resetPassword(values.email)
      setIsSuccess(true)
    } catch (err: any) {
      setErrorMessage(err?.message || 'Failed to send reset link. Please try again.')
    }
  }

  if (isSuccess) {
    return (
      <div className="text-center space-y-4">
        <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-emerald-100 text-emerald-600">
          <CheckCircle2 className="h-8 w-8" />
        </div>
        <h2 className="text-2xl font-bold tracking-tight text-slate-900">Reset link sent</h2>
        <p className="text-sm text-slate-600 leading-relaxed">
          If an account exists for that email, we’ve sent instructions to reset your password.
        </p>
        <div className="pt-4">
          <Link to="/login">
            <Button variant="outline" className="w-full">
              Back to Sign In
            </Button>
          </Link>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="text-center">
        <h2 className="text-2xl font-bold tracking-tight text-slate-900">Forgot your password?</h2>
        <p className="mt-1 text-sm text-slate-500">
          Enter your email and we’ll send you a password reset link.
        </p>
      </div>

      {errorMessage && (
        <div className="flex items-center gap-2.5 rounded-lg border border-rose-200 bg-rose-50 p-3.5 text-sm text-rose-800">
          <AlertCircle className="h-4 w-4 flex-shrink-0 text-rose-600" />
          <span>{errorMessage}</span>
        </div>
      )}

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        <div>
          <Label htmlFor="email" required>
            Email address
          </Label>
          <div className="mt-1.5">
            <Input
              id="email"
              type="email"
              autoComplete="email"
              placeholder="you@example.com"
              leftIcon={<Mail className="h-4 w-4" />}
              error={errors.email?.message}
              {...register('email')}
            />
          </div>
        </div>

        <Button type="submit" className="w-full" size="md" isLoading={isSubmitting}>
          Send Reset Link
        </Button>
      </form>

      <div className="text-center">
        <Link
          to="/login"
          className="inline-flex items-center text-sm font-semibold text-primary-600 hover:text-primary-700"
        >
          <ArrowLeft className="h-4 w-4 mr-1.5" />
          Back to Sign In
        </Link>
      </div>
    </div>
  )
}
export default ForgotPasswordPage
