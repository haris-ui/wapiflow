import React from 'react'
import { Link, useNavigate } from 'react-router-dom'
import {
  ShoppingCart,
  Clock,
  DollarSign,
  Plus,
  ArrowRight,
  Package,
  TrendingUp,
  AlertCircle,
} from 'lucide-react'
import { useBusiness } from '@/hooks/useBusiness'
import { useDashboardStats } from '@/hooks/useOrders'
import { Button } from '@/components/ui/Button'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card'
import { OrderStatusBadge } from '@/components/shared/OrderStatusBadge'
import { EmptyState } from '@/components/ui/EmptyState'
import { CardSkeleton, TableRowSkeleton } from '@/components/ui/Skeleton'
import { formatCurrency, formatDate } from '@/lib/utils'

export const DashboardPage: React.FC = () => {
  const navigate = useNavigate()
  const { activeBusiness } = useBusiness()
  const { data: stats, isLoading, isError, error, refetch } = useDashboardStats()

  if (!activeBusiness) {
    return (
      <EmptyState
        title="No Business Selected"
        description="Please select or create a business to view your dashboard metrics."
        actionLabel="Create Business"
        onAction={() => navigate('/onboarding/create-business')}
      />
    )
  }

  const currency = stats?.currency || activeBusiness.currency || 'USD'

  return (
    <div className="space-y-8">
      {/* Welcome & Actions Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900 sm:text-3xl">
            Welcome, {activeBusiness.name} 👋
          </h1>
          <p className="mt-1 text-sm text-slate-500">
            Real-time overview of your WhatsApp orders and sales performance.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Link to="/products/new">
            <Button variant="outline" size="md" leftIcon={<Package className="h-4 w-4" />}>
              Add Product
            </Button>
          </Link>
          <Link to="/orders/new">
            <Button variant="primary" size="md" leftIcon={<Plus className="h-4 w-4" />}>
              Create Order
            </Button>
          </Link>
        </div>
      </div>

      {isError && (
        <div className="flex items-center justify-between rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800">
          <div className="flex items-center gap-2">
            <AlertCircle className="h-5 w-5 text-rose-600" />
            <span>Failed to load dashboard metrics: {(error as any)?.message || 'Unknown error'}</span>
          </div>
          <Button variant="outline" size="sm" onClick={() => refetch()}>
            Retry
          </Button>
        </div>
      )}

      {/* KPI Stats Cards */}
      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3">
        {isLoading ? (
          <>
            <CardSkeleton />
            <CardSkeleton />
            <CardSkeleton />
          </>
        ) : (
          <>
            <Card className="hover:border-slate-300 transition-colors">
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-sm font-medium text-slate-500">Today's Orders</CardTitle>
                <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-blue-50 text-blue-600">
                  <ShoppingCart className="h-5 w-5" />
                </div>
              </CardHeader>
              <CardContent>
                <div className="text-3xl font-bold text-slate-900">
                  {stats?.today_orders_count ?? 0}
                </div>
                <p className="mt-1 text-xs text-slate-500 flex items-center gap-1">
                  <TrendingUp className="h-3 w-3 text-emerald-500" />
                  Received through store and WhatsApp
                </p>
              </CardContent>
            </Card>

            <Card className="hover:border-slate-300 transition-colors">
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-sm font-medium text-slate-500">Pending Orders</CardTitle>
                <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-amber-50 text-amber-600">
                  <Clock className="h-5 w-5" />
                </div>
              </CardHeader>
              <CardContent>
                <div className="text-3xl font-bold text-slate-900">
                  {stats?.pending_orders_count ?? 0}
                </div>
                <p className="mt-1 text-xs text-slate-500">Requires confirmation or preparation</p>
              </CardContent>
            </Card>

            <Card className="hover:border-slate-300 transition-colors">
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-sm font-medium text-slate-500">Today's Revenue</CardTitle>
                <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-emerald-50 text-emerald-600">
                  <DollarSign className="h-5 w-5" />
                </div>
              </CardHeader>
              <CardContent>
                <div className="text-3xl font-bold text-slate-900">
                  {formatCurrency(stats?.today_revenue ?? 0, currency)}
                </div>
                <p className="mt-1 text-xs text-slate-500">Calculated from completed & confirmed orders</p>
              </CardContent>
            </Card>
          </>
        )}
      </div>

      {/* Recent Orders Section */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold text-slate-900">Recent Orders</h2>
            <p className="text-sm text-slate-500">The 5 most recent customer orders</p>
          </div>
          <Link
            to="/orders"
            className="inline-flex items-center text-sm font-semibold text-primary-600 hover:text-primary-700"
          >
            View all orders
            <ArrowRight className="h-4 w-4 ml-1" />
          </Link>
        </div>

        <div className="rounded-xl border border-slate-200 bg-white overflow-hidden shadow-sm">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="bg-slate-50/75 border-b border-slate-200 text-xs font-semibold uppercase tracking-wider text-slate-500">
                <tr>
                  <th className="px-6 py-3.5">Order #</th>
                  <th className="px-6 py-3.5">Customer</th>
                  <th className="px-6 py-3.5">Status</th>
                  <th className="px-6 py-3.5">Amount</th>
                  <th className="px-6 py-3.5">Date</th>
                  <th className="px-6 py-3.5 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {isLoading ? (
                  Array.from({ length: 5 }).map((_, i) => (
                    <TableRowSkeleton key={i} columns={6} />
                  ))
                ) : !stats?.recent_orders || stats.recent_orders.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="py-12">
                      <EmptyState
                        title="No orders yet"
                        description="When customers place orders via WhatsApp or manually, they will appear here."
                        actionLabel="Create First Order"
                        onAction={() => navigate('/orders/new')}
                      />
                    </td>
                  </tr>
                ) : (
                  stats.recent_orders.map((order) => (
                    <tr
                      key={order.id}
                      onClick={() => navigate(`/orders/${order.id}`)}
                      className="cursor-pointer hover:bg-slate-50/80 transition-colors"
                    >
                      <td className="px-6 py-4 font-semibold text-primary-700">
                        #{order.order_number}
                      </td>
                      <td className="px-6 py-4">
                        <div className="font-medium text-slate-900">{order.customer?.name || 'Walk-in Customer'}</div>
                        <div className="text-xs text-slate-400">
                          {order.channel === 'whatsapp' ? 'WhatsApp' : 'Manual entry'}
                        </div>
                      </td>
                      <td className="px-6 py-4">
                        <OrderStatusBadge status={order.status} />
                      </td>
                      <td className="px-6 py-4 font-semibold text-slate-900">
                        {formatCurrency(order.total_amount, order.currency || currency)}
                      </td>
                      <td className="px-6 py-4 text-slate-500">
                        {formatDate(order.created_at, 'MMM d, h:mm a')}
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
                          View Details
                        </Button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  )
}
export default DashboardPage
