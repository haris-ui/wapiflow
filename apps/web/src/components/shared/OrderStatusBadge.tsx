import React from 'react'
import { Badge } from '@/components/ui/Badge'
import { ORDER_STATUS_LABELS } from '@/lib/constants'
import { OrderStatus } from '@/types'

export interface OrderStatusBadgeProps {
  status: OrderStatus
  className?: string
}

export const OrderStatusBadge: React.FC<OrderStatusBadgeProps> = ({ status, className }) => {
  const label = ORDER_STATUS_LABELS[status] || status

  return (
    <Badge variant={status} dot className={className}>
      {label}
    </Badge>
  )
}
