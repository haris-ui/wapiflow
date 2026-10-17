import React from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Phone, Mail, MapPin, ShoppingBag, Plus, AlertCircle } from 'lucide-react'
import { useCustomer, useCustomerOrders } from '@/hooks/useCustomers'
import { useBusiness } from '@/hooks/useBusiness'
import { PageHeader } from '@/components/shared/PageHeader'
import { Button } from '@/components/ui/Button'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card'
import { OrderStatusBadge } from '@/components/shared/OrderStatusBadge'
import { Skeleton } from '@/components/ui/Skeleton'
import { EmptyState } from '@/components/ui/EmptyState'
import { formatCurrency, formatDate } from '@/lib/utils'

export const CustomerDetailPage: React.FC = () => {
  const { customerId } = useParams<{ customerId: string }>()
  const navigate = useNavigate()
  const { activeBusiness } = useBusiness()

  const { data: customer, isLoading: isLoadingCustomer, isError, error } = useCustomer(customerId)
  const { data: orders = [], isLoading: isLoadingOrders } = useCustomerOrders(customerId)

  if (isLoadingCustomer) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-48" />
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <Skeleton className="h-64 rounded-xl" />
          <Skeleton className="lg:col-span-2 h-96 rounded-xl" />
        </div>
      </div>
    )
  }

  if (isError || !customer) {
    return (
      <div className="rounded-xl border border-rose-200 bg-rose-50 p-6 text-center space-y-4">
        <div className="inline-flex h-12 w-12 items-center justify-center rounded-full bg-rose-100 text-rose-600">
          <AlertCircle className="h-6 w-6" />
        </div>
        <h2 className="text-lg font-bold text-slate-900">Customer Not Found</h2>
        <p className="text-sm text-slate-600 max-w-sm mx-auto">
          {(error as any)?.message || 'We could not locate this customer record.'}
        </p>
        <Button variant="outline" onClick={() => navigate('/customers')}>
          Back to Customers
        </Button>
      </div>
    )
  }

  const currency = activeBusiness?.currency || 'USD'
  const totalSpent = orders.reduce((sum, o) => sum + (Number(o.total_amount) || 0), 0)

  return (
    <div className="space-y-6">
      <PageHeader
        title={customer.name}
        description={`Customer since ${formatDate(customer.created_at, 'MMMM yyyy')}`}
        backUrl="/customers"
        backLabel="Back to Customers"
        actions={
          <Button
            variant="primary"
            size="md"
            leftIcon={<Plus className="h-4 w-4" />}
            onClick={() => navigate('/orders/new')}
          >
            New Order
          </Button>
        }
      />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Customer Profile Card */}
        <div className="space-y-6">
          <Card>
            <CardHeader className="border-b border-slate-100 pb-4">
              <CardTitle className="text-base font-semibold">Contact Details</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4 pt-4">
              <div className="flex items-center gap-3 text-sm text-slate-700">
                <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-slate-100 text-slate-500 flex-shrink-0">
                  <Phone className="h-4 w-4" />
                </div>
                <div>
                  <p className="text-xs text-slate-400 font-medium">WhatsApp Phone</p>
                  <p className="font-mono text-sm">{customer.phone_number}</p>
                </div>
              </div>

              {customer.email && (
                <div className="flex items-center gap-3 text-sm text-slate-700">
                  <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-slate-100 text-slate-500 flex-shrink-0">
                    <Mail className="h-4 w-4" />
                  </div>
                  <div>
                    <p className="text-xs text-slate-400 font-medium">Email</p>
                    <a href={`mailto:${customer.email}`} className="text-primary-600 hover:underline">
                      {customer.email}
                    </a>
                  </div>
                </div>
              )}

              {(customer.address || customer.city) && (
                <div className="flex items-start gap-3 text-sm text-slate-700">
                  <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-slate-100 text-slate-500 flex-shrink-0 mt-0.5">
                    <MapPin className="h-4 w-4" />
                  </div>
                  <div>
                    <p className="text-xs text-slate-400 font-medium">Address</p>
                    {customer.address && <p>{customer.address}</p>}
                    {customer.city && <p className="text-slate-500">{customer.city}</p>}
                  </div>
                </div>
              )}

              {customer.notes && (
                <div className="pt-2 border-t border-slate-100">
                  <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1">
                    Notes
                  </p>
                  <p className="text-xs text-slate-600 bg-slate-50 p-2.5 rounded-lg border border-slate-100">
                    {customer.notes}
                  </p>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Quick Stats */}
          <Card>
            <CardHeader className="border-b border-slate-100 pb-4">
              <CardTitle className="text-base font-semibold">Customer Metrics</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4 pt-4">
              <div className="flex justify-between items-center">
                <span className="text-sm text-slate-500">Total Orders</span>
                <span className="font-bold text-slate-900">{orders.length}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm text-slate-500">Lifetime Spent</span>
                <span className="font-bold text-primary-700">
                  {formatCurrency(totalSpent, currency)}
                </span>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Customer Orders Table */}
        <div className="lg:col-span-2">
          <Card>
            <CardHeader className="border-b border-slate-100 flex flex-row items-center justify-between">
              <CardTitle className="text-base font-semibold flex items-center gap-2">
                <ShoppingBag className="h-4 w-4 text-slate-500" />
                Order History ({orders.length})
              </CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm">
                  <thead className="bg-slate-50/75 border-b border-slate-200 text-xs font-semibold uppercase tracking-wider text-slate-500">
                    <tr>
                      <th className="px-6 py-3.5">Order #</th>
                      <th className="px-6 py-3.5">Date</th>
                      <th className="px-6 py-3.5">Status</th>
                      <th className="px-6 py-3.5">Amount</th>
                      <th className="px-6 py-3.5 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {isLoadingOrders ? (
                      Array.from({ length: 4 }).map((_, i) => (
                        <tr key={i} className="animate-pulse">
                          <td colSpan={5} className="p-4">
                            <Skeleton className="h-4 w-full" />
                          </td>
                        </tr>
                      ))
                    ) : orders.length === 0 ? (
                      <tr>
                        <td colSpan={5} className="py-12">
                          <EmptyState
                            title="No orders yet"
                            description="This customer hasn’t placed any orders yet."
                            actionLabel="Create Order"
                            onAction={() => navigate('/orders/new')}
                          />
                        </td>
                      </tr>
                    ) : (
                      orders.map((order) => (
                        <tr
                          key={order.id}
                          onClick={() => navigate(`/orders/${order.id}`)}
                          className="cursor-pointer hover:bg-slate-50/80 transition-colors"
                        >
                          <td className="px-6 py-4 font-semibold text-primary-700">
                            #{order.order_number}
                          </td>
                          <td className="px-6 py-4 text-slate-500">
                            {formatDate(order.created_at, 'MMM d, yyyy')}
                          </td>
                          <td className="px-6 py-4">
                            <OrderStatusBadge status={order.status} />
                          </td>
                          <td className="px-6 py-4 font-semibold text-slate-900">
                            {formatCurrency(order.total_amount, order.currency || currency)}
                          </td>
                          <td className="px-6 py-4 text-right">
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={(e) => {
                                e.stopPropagation()
                                navigate(`/orders/${order.id}`)
                              }}
                            >
                              View
                            </Button>
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}
export default CustomerDetailPage
