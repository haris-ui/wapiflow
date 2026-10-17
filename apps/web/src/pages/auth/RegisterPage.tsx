import React, { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Link } from 'react-router-dom'
import { Mail, Lock, User, CheckCircle2, AlertCircle } from 'lucide-react'
import { useAuth } from '@/hooks/useAuth'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Label } from '@/components/ui/Label'

const registerSchema = z
  .object({
    fullName: z.string().min(2, 'Full name must be at least 2 characters'),
    email: z.string().email('Please enter a valid email address'),
    password: z.string().min(8, 'Password must be at least 8 characters'),
    confirmPassword: z.string().min(8, 'Please confirm your password'),
  })
  .refine((data) => data.password === data.confirmPassword, {
    message: 'Passwords do not match',
    path: ['confirmPassword'],
  })

type RegisterFormValues = z.infer<typeof registerSchema>

export const RegisterPage: React.FC = () => {
  const { signUp } = useAuth()
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [isSuccess, setIsSuccess] = useState<boolean>(false)

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<RegisterFormValues>({
    resolver: zodResolver(registerSchema),
    defaultValues: {
      fullName: '',
      email: '',
      password: '',
      confirmPassword: '',
    },
  })

  const onSubmit = async (values: RegisterFormValues) => {
    try {
      setErrorMessage(null)
      await signUp(values.email, values.password, values.fullName)
      setIsSuccess(true)
    } catch (err: any) {
      setErrorMessage(err?.message || 'Failed to create account. Please try again.')
    }
  }

  if (isSuccess) {
    return (
      <div className="text-center space-y-4">
        <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-emerald-100 text-emerald-600">
          <CheckCircle2 className="h-8 w-8" />
        </div>
        <h2 className="text-2xl font-bold tracking-tight text-slate-900">Check your email</h2>
        <p className="text-sm text-slate-600 leading-relaxed">
          We’ve sent a verification link to your email address. Please click the link to activate
          your WapiFlow account.
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
        <h2 className="text-2xl font-bold tracking-tight text-slate-900">Create an account</h2>
        <p className="mt-1 text-sm text-slate-500">Start streamlining your WhatsApp orders today</p>
      </div>

      {errorMessage && (
        <div className="flex items-center gap-2.5 rounded-lg border border-rose-200 bg-rose-50 p-3.5 text-sm text-rose-800">
          <AlertCircle className="h-4 w-4 flex-shrink-0 text-rose-600" />
          <span>{errorMessage}</span>
        </div>
      )}

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        <div>
          <Label htmlFor="fullName" required>
            Full Name
          </Label>
          <div className="mt-1.5">
            <Input
              id="fullName"
              placeholder="Sarah Jenkins"
              leftIcon={<User className="h-4 w-4" />}
              error={errors.fullName?.message}
              {...register('fullName')}
            />
          </div>
        </div>

        <div>
          <Label htmlFor="email" required>
            Email address
          </Label>
          <div className="mt-1.5">
            <Input
              id="email"
              type="email"
              placeholder="you@example.com"
              leftIcon={<Mail className="h-4 w-4" />}
              error={errors.email?.message}
              {...register('email')}
            />
          </div>
        </div>

        <div>
          <Label htmlFor="password" required>
            Password
          </Label>
          <div className="mt-1.5">
            <Input
              id="password"
              type="password"
              placeholder="••••••••"
              leftIcon={<Lock className="h-4 w-4" />}
              error={errors.password?.message}
              {...register('password')}
            />
          </div>
        </div>

        <div>
          <Label htmlFor="confirmPassword" required>
            Confirm Password
          </Label>
          <div className="mt-1.5">
            <Input
              id="confirmPassword"
              type="password"
              placeholder="••••••••"
              leftIcon={<Lock className="h-4 w-4" />}
              error={errors.confirmPassword?.message}
              {...register('confirmPassword')}
            />
          </div>
        </div>

        <Button type="submit" className="w-full" size="md" isLoading={isSubmitting}>
          Create account
        </Button>
      </form>

      <div className="text-center text-sm text-slate-500">
        Already have an account?{' '}
        <Link to="/login" className="font-semibold text-primary-600 hover:text-primary-700">
          Sign in
        </Link>
      </div>
    </div>
  )
}
export default RegisterPage
