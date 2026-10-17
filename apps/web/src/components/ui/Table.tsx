import React from 'react'
import { cn } from '@/lib/utils'
import { TableRowSkeleton } from '@/components/ui/Skeleton'

export interface TableProps extends React.HTMLAttributes<HTMLTableElement> {
  stickyHeader?: boolean
}

export const Table = React.forwardRef<HTMLTableElement, TableProps>(
  ({ className, stickyHeader, ...props }, ref) => (
    <div className="relative w-full overflow-auto rounded-xl border border-slate-200 bg-white shadow-sm">
      <table
        ref={ref}
        className={cn('w-full caption-bottom text-sm', className)}
        {...props}
      />
    </div>
  )
)
Table.displayName = 'Table'

export const TableHeader = React.forwardRef<
  HTMLTableSectionElement,
  React.HTMLAttributes<HTMLTableSectionElement> & { sticky?: boolean }
>(({ className, sticky, ...props }, ref) => (
  <thead
    ref={ref}
    className={cn(
      'border-b border-slate-200 bg-slate-50/75 text-xs font-semibold uppercase tracking-wider text-slate-500',
      sticky && 'sticky top-0 z-10 backdrop-blur-sm',
      className
    )}
    {...props}
  />
))
TableHeader.displayName = 'TableHeader'

export const TableBody = React.forwardRef<
  HTMLTableSectionElement,
  React.HTMLAttributes<HTMLTableSectionElement> & {
    isLoading?: boolean
    skeletonRows?: number
    skeletonCols?: number
  }
>(({ className, isLoading, skeletonRows = 5, skeletonCols = 5, children, ...props }, ref) => (
  <tbody ref={ref} className={cn('[&_tr:last-child]:border-0', className)} {...props}>
    {isLoading
      ? Array.from({ length: skeletonRows }).map((_, idx) => (
          <TableRowSkeleton key={idx} columns={skeletonCols} />
        ))
      : children}
  </tbody>
))
TableBody.displayName = 'TableBody'

export const TableRow = React.forwardRef<
  HTMLTableRowElement,
  React.HTMLAttributes<HTMLTableRowElement>
>(({ className, ...props }, ref) => (
  <tr
    ref={ref}
    className={cn(
      'border-b border-slate-100 transition-colors hover:bg-slate-50/80 data-[state=selected]:bg-slate-100',
      className
    )}
    {...props}
  />
))
TableRow.displayName = 'TableRow'

export const TableHead = React.forwardRef<
  HTMLTableCellElement,
  React.ThHTMLAttributes<HTMLTableCellElement>
>(({ className, ...props }, ref) => (
  <th
    ref={ref}
    className={cn(
      'h-11 px-4 text-left align-middle font-medium text-slate-600 [&:has([role=checkbox])]:pr-0',
      className
    )}
    {...props}
  />
))
TableHead.displayName = 'TableHead'

export const TableCell = React.forwardRef<
  HTMLTableCellElement,
  React.TdHTMLAttributes<HTMLTableCellElement>
>(({ className, ...props }, ref) => (
  <td
    ref={ref}
    className={cn('p-4 align-middle [&:has([role=checkbox])]:pr-0 text-slate-700', className)}
    {...props}
  />
))
TableCell.displayName = 'TableCell'
