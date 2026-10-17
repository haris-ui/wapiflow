import React, { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  Package,
  User,
  Phone,
  Mail,
  MapPin,
  Clock,
  AlertCircle,
  FileText,
} from 'lucide-react'
import { useOrder, useUpdateOrderStatus } from '@/hooks/useOrders'
import { useBusiness } from '@/hooks/useBusiness'
import { PageHeader } from '@/components/shared/PageHeader'
import { OrderStatusBadge } from '@/components/shared/OrderStatusBadge'
import { Button } from '@/components/ui/Button'
import { Select } from '@/components/ui/Select'
import { ConfirmDialog } from '@/components/shared/ConfirmDialog'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card'
import { Skeleton } from '@/components/ui/Skeleton'
import { ORDER_STATUSES, ORDER_STATUS_LABELS } from '@/lib/constants'
import { formatCurrency, formatDate } from '@/lib/utils'
import { OrderStatus } from '@/types'
import { useToast } from '@/components/ui/Toast'

export const OrderDetailPage: React.FC = () => {
  const { orderId } = useParams<{ orderId: string }>()
  const navigate = useNavigate()
  const { toast } = useToast()
  const { activeBusiness } = useBusiness()

  const { data: order, isLoading, isError, error } = useOrder(orderId)
  const updateStatusMutation = useUpdateOrderStatus()

  const [newStatus, setNewStatus] = useState<OrderStatus | ''>('')
  const [statusComment, setStatusComment] = useState<string>('')
  const [isConfirmOpen, setIsConfirmOpen] = useState<boolean>(false)

  const handleInitiateStatusChange = (status: OrderStatus) => {
    if (status === order?.status) return
    setNewStatus(status)
    setIsConfirmOpen(true)
  }

  const handleConfirmStatusChange = async () => {
    if (!orderId || !newStatus) return

    try {
      await updateStatusMutation.mutateAsync({
        orderId,
        statusUpdate: {
          status: newStatus,
          comment: statusComment || undefined,
        },
      })
      toast({
        title: 'Status Updated',
        description: `Order #${order?.order_number} status changed to ${ORDER_STATUS_LABELS[newStatus]}.`,
        type: 'success',
      })
      setIsConfirmOpen(false)
      setStatusComment('')
      setNewStatus('')
    } catch (err: any) {
      toast({
        title: 'Error updating status',
        description: err.message || 'Failed to update order status.',
        type: 'error',
      })
    }
  }

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-48" />
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 space-y-6">
            <Skeleton className="h-64 w-full rounded-xl" />
            <Skeleton className="h-48 w-full rounded-xl" />
          </div>
          <div className="space-y-6">
            <Skeleton className="h-48 w-full rounded-xl" />
            <Skeleton className="h-48 w-full rounded-xl" />
          </div>
        </div>
      </div>
    )
  }

  if (isError || !order) {
    return (
      <div className="rounded-xl border border-rose-200 bg-rose-50 p-6 text-center space-y-4">
        <div className="inline-flex h-12 w-12 items-center justify-center rounded-full bg-rose-100 text-rose-600">
          <AlertCircle className="h-6 w-6" />
        </div>
        <h2 className="text-lg font-bold text-slate-900">Order Not Found</h2>
        <p className="text-sm text-slate-600 max-w-sm mx-auto">
          {(error as any)?.message || 'We could not locate this order. It may have been removed.'}
        </p>
        <Button variant="outline" onClick={() => navigate('/orders')}>
          Back to Orders
        </Button>
      </div>
    )
  }

  const currency = order.currency || activeBusiness?.currency || 'USD'

  return (
    <div className="space-y-6">
      <PageHeader
        title={`Order #${order.order_number}`}
        description={`Placed on ${formatDate(order.created_at)} via ${
          order.channel === 'whatsapp' ? 'WhatsApp' : 'Manual Entry'
        }`}
        backUrl="/orders"
        backLabel="Back to Orders"
        actions={
          <div className="flex items-center gap-3">
            <OrderStatusBadge status={order.status} className="text-sm px-3 py-1" />
            <div className="w-44">
              <Select
                value={order.status}
                onChange={(e) => handleInitiateStatusChange(e.target.value as OrderStatus)}
                disabled={updateStatusMutation.isPending}
              >
                {ORDER_STATUSES.map((status) => (
                  <option key={status} value={status}>
                    Change to {ORDER_STATUS_LABELS[status]}
                  </option>
                ))}
              </Select>
            </div>
          </div>
        }
      />

      {/* Grid Content */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Items & Totals */}
        <div className="lg:col-span-2 space-y-6">
          <Card>
            <CardHeader className="border-b border-slate-100">
              <CardTitle className="text-base font-semibold flex items-center gap-2">
                <Package className="h-4 w-4 text-slate-500" />
                Order Items ({order.items?.length || 0})
              </CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              <div className="divide-y divide-slate-100">
                {order.items && order.items.length > 0 ? (
                  order.items.map((item, index) => (
                    <div key={item.id || index} className="flex items-center justify-between p-4 sm:p-6">
                      <div className="space-y-0.5">
                        <p className="font-medium text-slate-900">{item.product_name}</p>
                        <p className="text-xs text-slate-500">
                          {formatCurrency(item.unit_price, currency)} &times; {item.quantity}
                        </p>
                      </div>
                      <div className="font-semibold text-slate-900">
                        {formatCurrency(item.total_price || item.unit_price * item.quantity, currency)}
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="p-6 text-center text-sm text-slate-500">No items in this order</div>
                )}
              </div>

              {/* Totals Breakdown */}
              <div className="bg-slate-50/60 p-6 border-t border-slate-100 space-y-2 text-sm">
                <div className="flex justify-between text-slate-600">
                  <span>Subtotal</span>
                  <span>{formatCurrency(order.subtotal || 0, currency)}</span>
                </div>
                {Number(order.shipping_fee) > 0 && (
                  <div className="flex justify-between text-slate-600">
                    <span>Shipping Fee</span>
                    <span>{formatCurrency(order.shipping_fee, currency)}</span>
                  </div>
                )}
                {Number(order.tax) > 0 && (
                  <div className="flex justify-between text-slate-600">
                    <span>Tax</span>
                    <span>{formatCurrency(order.tax, currency)}</span>
                  </div>
                )}
                {Number(order.discount) > 0 && (
                  <div className="flex justify-between text-emerald-600">
                    <span>Discount</span>
                    <span>-{formatCurrency(order.discount, currency)}</span>
                  </div>
                )}
                <div className="flex justify-between border-t border-slate-200 pt-3 text-base font-bold text-slate-900">
                  <span>Total Amount</span>
                  <span>{formatCurrency(order.total_amount, currency)}</span>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Customer Order Notes */}
          {order.notes && (
            <Card>
              <CardHeader>
                <CardTitle className="text-base font-semibold flex items-center gap-2">
                  <FileText className="h-4 w-4 text-slate-500" />
                  Order Notes
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-slate-700 whitespace-pre-wrap bg-slate-50 p-4 rounded-lg border border-slate-100">
                  {order.notes}
                </p>
              </CardContent>
            </Card>
          )}

          {/* Status Timeline History */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base font-semibold flex items-center gap-2">
                <Clock className="h-4 w-4 text-slate-500" />
                Status History
              </CardTitle>
            </CardHeader>
            <CardContent>
              {order.history && order.history.length > 0 ? (
                <div className="relative pl-6 space-y-6 before:absolute before:left-2 before:top-2 before:bottom-2 before:w-0.5 before:bg-slate-200">
                  {order.history.map((hist, idx) => (
                    <div key={hist.id || idx} className="relative">
                      <div className="absolute -left-6 top-1 h-4 w-4 rounded-full border-2 border-white bg-primary-600 shadow-sm" />
                      <div>
                        <div className="flex items-center gap-2">
                          <OrderStatusBadge status={hist.status} />
                          <span className="text-xs text-slate-400">
                            {formatDate(hist.created_at)}
                          </span>
                        </div>
                        {hist.comment && (
                          <p className="mt-1 text-xs text-slate-600 bg-slate-50 p-2 rounded">
                            {hist.comment}
                          </p>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-xs text-slate-400 italic">
                  Order was created with status{' '}
                  <span className="font-semibold text-slate-700">{order.status}</span> on{' '}
                  {formatDate(order.created_at)}.
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Right Column: Customer Info */}
        <div className="space-y-6">
          <Card>
            <CardHeader className="border-b border-slate-100">
              <CardTitle className="text-base font-semibold flex items-center gap-2">
                <User className="h-4 w-4 text-slate-500" />
                Customer Details
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4 pt-4">
              <div>
                <p className="font-semibold text-slate-900 text-base">{order.customer?.name || 'Walk-in Customer'}</p>
              </div>

              {order.customer?.phone_number && (
                <div className="flex items-center gap-3 text-sm text-slate-600">
                  <Phone className="h-4 w-4 text-slate-400 flex-shrink-0" />
                  <span>{order.customer.phone_number}</span>
                </div>
              )}

              {order.customer?.email && (
                <div className="flex items-center gap-3 text-sm text-slate-600">
                  <Mail className="h-4 w-4 text-slate-400 flex-shrink-0" />
                  <a href={`mailto:${order.customer.email}`} className="text-primary-600 hover:underline">
                    {order.customer.email}
                  </a>
                </div>
              )}

              {(order.customer?.address || order.customer?.city) && (
                <div className="flex items-start gap-3 text-sm text-slate-600">
                  <MapPin className="h-4 w-4 text-slate-400 flex-shrink-0 mt-0.5" />
                  <div>
                    {order.customer.address && <p>{order.customer.address}</p>}
                    {order.customer.city && <p className="text-slate-500">{order.customer.city}</p>}
                  </div>
                </div>
              )}

              {order.customer?.id && (
                <div className="pt-2 border-t border-slate-100">
                  <Button
                    variant="outline"
                    size="sm"
                    className="w-full text-xs"
                    onClick={() => navigate(`/customers/${order.customer.id}`)}
                  >
                    View Customer Profile
                  </Button>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Order Details Meta */}
          <Card>
            <CardHeader className="border-b border-slate-100">
              <CardTitle className="text-base font-semibold">Order Metadata</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 pt-4 text-xs">
              <div className="flex justify-between">
                <span className="text-slate-400">Order ID:</span>
                <span className="font-mono text-slate-700">{order.id}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Channel:</span>
                <span className="capitalize font-medium text-slate-700">{order.channel}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Created:</span>
                <span className="text-slate-700">{formatDate(order.created_at)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Updated:</span>
                <span className="text-slate-700">{formatDate(order.updated_at)}</span>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Confirmation Dialog for Status Change */}
      <ConfirmDialog
        isOpen={isConfirmOpen}
        onClose={() => setIsConfirmOpen(false)}
        onConfirm={handleConfirmStatusChange}
        isLoading={updateStatusMutation.isPending}
        title="Update Order Status"
        description={`Are you sure you want to change order #${order.order_number} to "${
          newStatus ? ORDER_STATUS_LABELS[newStatus] : ''
        }"?`}
        confirmText="Confirm Status Update"
      />
    </div>
  )
}
export default OrderDetailPage
