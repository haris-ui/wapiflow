import React, { forwardRef } from 'react'
import * as LabelPrimitive from '@radix-ui/react-label'
import { cn } from '@/lib/utils'

export interface LabelProps
  extends React.ComponentPropsWithoutRef<typeof LabelPrimitive.Root> {
  required?: boolean
}

export const Label = forwardRef<React.ElementRef<typeof LabelPrimitive.Root>, LabelProps>(
  ({ className, required, children, ...props }, ref) => {
    return (
      <LabelPrimitive.Root
        ref={ref}
        className={cn(
          'text-sm font-medium leading-none text-slate-700 peer-disabled:cursor-not-allowed peer-disabled:opacity-70 select-none flex items-center gap-1',
          className
        )}
        {...props}
      >
        {children}
        {required && <span className="text-rose-500 font-semibold">*</span>}
      </LabelPrimitive.Root>
    )
  }
)

Label.displayName = LabelPrimitive.Root.displayName
