import React, { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useNavigate } from 'react-router-dom'
import { Building2, Mail, Phone, AlertCircle } from 'lucide-react'
import { useBusiness } from '@/hooks/useBusiness'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Label } from '@/components/ui/Label'
import { Select } from '@/components/ui/Select'
import { CURRENCIES, TIMEZONES } from '@/lib/constants'

const createBusinessSchema = z.object({
  name: z.string().min(2, 'Business name must be at least 2 characters'),
  email: z.string().email('Please enter a valid business email').optional().or(z.literal('')),
  phone_number: z.string().optional().or(z.literal('')),
  currency: z.string().min(1, 'Please select a currency'),
  timezone: z.string().min(1, 'Please select a timezone'),
})

type CreateBusinessFormValues = z.infer<typeof createBusinessSchema>

export const CreateBusinessPage: React.FC = () => {
  const { createBusiness } = useBusiness()
  const navigate = useNavigate()
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<CreateBusinessFormValues>({
    resolver: zodResolver(createBusinessSchema),
    defaultValues: {
      name: '',
      email: '',
      phone_number: '',
      currency: 'USD',
      timezone: 'UTC',
    },
  })

  const onSubmit = async (values: CreateBusinessFormValues) => {
    try {
      setErrorMessage(null)
      await createBusiness({
        name: values.name,
        email: values.email || undefined,
        phone_number: values.phone_number || undefined,
        currency: values.currency,
        timezone: values.timezone,
      })
      navigate('/dashboard')
    } catch (err: any) {
      setErrorMessage(err?.message || 'Failed to create business. Please try again.')
    }
  }

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col justify-center py-12 px-4 sm:px-6 lg:px-8">
      <div className="sm:mx-auto sm:w-full sm:max-w-xl">
        <div className="text-center mb-8">
          <div className="inline-flex h-12 w-12 items-center justify-center rounded-2xl bg-primary-100 text-primary-700 mb-3 shadow-inner">
            <Building2 className="h-6 w-6" />
          </div>
          <h1 className="text-3xl font-extrabold text-slate-900 tracking-tight">
            Set up your Business
          </h1>
          <p className="mt-2 text-sm text-slate-600">
            Tell us about your company to configure your WhatsApp store and order processing.
          </p>
        </div>

        <div className="bg-white py-8 px-6 shadow-sm border border-slate-200 rounded-2xl sm:px-10">
          {errorMessage && (
            <div className="mb-6 flex items-center gap-2.5 rounded-lg border border-rose-200 bg-rose-50 p-3.5 text-sm text-rose-800">
              <AlertCircle className="h-4 w-4 flex-shrink-0 text-rose-600" />
              <span>{errorMessage}</span>
            </div>
          )}

          <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
            <div>
              <Label htmlFor="name" required>
                Business / Brand Name
              </Label>
              <div className="mt-1.5">
                <Input
                  id="name"
                  placeholder="e.g. Acme Coffee Roasters"
                  leftIcon={<Building2 className="h-4 w-4" />}
                  error={errors.name?.message}
                  {...register('name')}
                />
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <Label htmlFor="email">Support Email</Label>
                <div className="mt-1.5">
                  <Input
                    id="email"
                    type="email"
                    placeholder="orders@acmecoffee.com"
                    leftIcon={<Mail className="h-4 w-4" />}
                    error={errors.email?.message}
                    {...register('email')}
                  />
                </div>
              </div>

              <div>
                <Label htmlFor="phone_number">WhatsApp Phone Number</Label>
                <div className="mt-1.5">
                  <Input
                    id="phone_number"
                    type="tel"
                    placeholder="+1234567890"
                    leftIcon={<Phone className="h-4 w-4" />}
                    error={errors.phone_number?.message}
                    {...register('phone_number')}
                  />
                </div>
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <Label htmlFor="currency" required>
                  Operating Currency
                </Label>
                <div className="mt-1.5">
                  <Select
                    id="currency"
                    error={errors.currency?.message}
                    {...register('currency')}
                  >
                    {CURRENCIES.map((c) => (
                      <option key={c.code} value={c.code}>
                        {c.label}
                      </option>
                    ))}
                  </Select>
                </div>
              </div>

              <div>
                <Label htmlFor="timezone" required>
                  Store Timezone
                </Label>
                <div className="mt-1.5">
                  <Select
                    id="timezone"
                    error={errors.timezone?.message}
                    {...register('timezone')}
                  >
                    {TIMEZONES.map((tz) => (
                      <option key={tz} value={tz}>
                        {tz}
                      </option>
                    ))}
                  </Select>
                </div>
              </div>
            </div>

            <div className="pt-4">
              <Button type="submit" size="lg" className="w-full" isLoading={isSubmitting}>
                Complete Setup & Go to Dashboard
              </Button>
            </div>
          </form>
        </div>
      </div>
    </div>
  )
}
export default CreateBusinessPage
