import React from 'react'
import { ChevronLeft } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { Button } from '@/components/ui/Button'
import { cn } from '@/lib/utils'

export interface PageHeaderProps {
  title: string
  description?: string
  backUrl?: string
  backLabel?: string
  actions?: React.ReactNode
  className?: string
}

export const PageHeader: React.FC<PageHeaderProps> = ({
  title,
  description,
  backUrl,
  backLabel = 'Back',
  actions,
  className,
}) => {
  const navigate = useNavigate()

  return (
    <div className={cn('mb-6 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between', className)}>
      <div className="space-y-1">
        {backUrl && (
          <Button
            variant="ghost"
            size="sm"
            onClick={() => navigate(backUrl)}
            className="-ml-2 mb-1 text-slate-500 hover:text-slate-900 h-7 px-2"
          >
            <ChevronLeft className="h-4 w-4 mr-1" />
            {backLabel}
          </Button>
        )}
        <h1 className="text-2xl font-bold tracking-tight text-slate-900">{title}</h1>
        {description && <p className="text-sm text-slate-500">{description}</p>}
      </div>
      {actions && <div className="flex items-center gap-2.5 flex-wrap">{actions}</div>}
    </div>
  )
}
