import React from 'react'
import { cn } from '@/lib/utils'

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?:
    | 'default'
    | 'secondary'
    | 'outline'
    | 'destructive'
    | 'pending'
    | 'confirmed'
    | 'preparing'
    | 'ready'
    | 'shipped'
    | 'delivered'
    | 'cancelled'
  dot?: boolean
}

export const Badge: React.FC<BadgeProps> = ({
  className,
  variant = 'default',
  dot = false,
  children,
  ...props
}) => {
  const variantStyles = {
    default: 'bg-primary-100 text-primary-800 border-primary-200',
    secondary: 'bg-slate-100 text-slate-700 border-slate-200',
    outline: 'border-slate-300 text-slate-700 bg-transparent',
    destructive: 'bg-rose-100 text-rose-800 border-rose-200',
    pending: 'bg-amber-50 text-amber-800 border-amber-200',
    confirmed: 'bg-blue-50 text-blue-800 border-blue-200',
    preparing: 'bg-purple-50 text-purple-800 border-purple-200',
    ready: 'bg-orange-50 text-orange-800 border-orange-200',
    shipped: 'bg-cyan-50 text-cyan-800 border-cyan-200',
    delivered: 'bg-emerald-50 text-emerald-800 border-emerald-200',
    cancelled: 'bg-rose-50 text-rose-800 border-rose-200',
  }

  const dotColors = {
    default: 'bg-primary-500',
    secondary: 'bg-slate-500',
    outline: 'bg-slate-400',
    destructive: 'bg-rose-500',
    pending: 'bg-amber-500',
    confirmed: 'bg-blue-500',
    preparing: 'bg-purple-500',
    ready: 'bg-orange-500',
    shipped: 'bg-cyan-500',
    delivered: 'bg-emerald-500',
    cancelled: 'bg-rose-500',
  }

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-medium tracking-wide uppercase transition-colors',
        variantStyles[variant],
        className
      )}
      {...props}
    >
      {dot && (
        <span
          className={cn('h-1.5 w-1.5 rounded-full', dotColors[variant])}
          aria-hidden="true"
        />
      )}
      {children}
    </span>
  )
}
