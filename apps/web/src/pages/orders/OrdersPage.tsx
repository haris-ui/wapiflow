import React, { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Plus, Search, RefreshCw, Eye } from 'lucide-react'
import { useOrders } from '@/hooks/useOrders'
import { useBusiness } from '@/hooks/useBusiness'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Select } from '@/components/ui/Select'
import { PageHeader } from '@/components/shared/PageHeader'
import { OrderStatusBadge } from '@/components/shared/OrderStatusBadge'
import { Pagination } from '@/components/ui/Pagination'
import { EmptyState } from '@/components/ui/EmptyState'
import { TableRowSkeleton } from '@/components/ui/Skeleton'
import { ORDER_STATUSES, ORDER_STATUS_LABELS } from '@/lib/constants'
import { formatCurrency, formatDate } from '@/lib/utils'
import { OrderStatus } from '@/types'

export const OrdersPage: React.FC = () => {
  const navigate = useNavigate()
  const { activeBusiness } = useBusiness()

  const [page, setPage] = useState<number>(1)
  const [pageSize] = useState<number>(10)
  const [searchTerm, setSearchTerm] = useState<string>('')
  const [selectedStatus, setSelectedStatus] = useState<OrderStatus | ''>('')
  const [startDate, setStartDate] = useState<string>('')
  const [endDate, setEndDate] = useState<string>('')

  const {
    data,
    isLoading,
    isError,
    error,
    refetch,
  } = useOrders({
    page,
    pageSize,
    search: searchTerm,
    status: selectedStatus,
    startDate,
    endDate,
  })

  const orders = data?.items || []
  const total = data?.total || 0
  const totalPages = data?.total_pages || Math.ceil(total / pageSize) || 1

  const handleResetFilters = () => {
    setSearchTerm('')
    setSelectedStatus('')
    setStartDate('')
    setEndDate('')
    setPage(1)
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Orders"
        description="Monitor, update, and manage all your WhatsApp and direct sales."
        actions={
          <Link to="/orders/new">
            <Button variant="primary" size="md" leftIcon={<Plus className="h-4 w-4" />}>
              New Order
            </Button>
          </Link>
        }
      />

      {/* Filter and Search Bar */}
      <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm space-y-4">
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <div className="relative">
            <Input
              placeholder="Search by order # or customer..."
              leftIcon={<Search className="h-4 w-4" />}
              value={searchTerm}
              onChange={(e) => {
                setSearchTerm(e.target.value)
                setPage(1)
              }}
            />
          </div>

          <div>
            <Select
              value={selectedStatus}
              onChange={(e) => {
                setSelectedStatus(e.target.value as OrderStatus | '')
                setPage(1)
              }}
            >
              <option value="">All Statuses</option>
              {ORDER_STATUSES.map((status) => (
                <option key={status} value={status}>
                  {ORDER_STATUS_LABELS[status]}
                </option>
              ))}
            </Select>
          </div>

          <div>
            <Input
              type="date"
              placeholder="From Date"
              value={startDate}
              onChange={(e) => {
                setStartDate(e.target.value)
                setPage(1)
              }}
            />
          </div>

          <div>
            <Input
              type="date"
              placeholder="To Date"
              value={endDate}
              onChange={(e) => {
                setEndDate(e.target.value)
                setPage(1)
              }}
            />
          </div>
        </div>

        {(searchTerm || selectedStatus || startDate || endDate) && (
          <div className="flex items-center justify-between pt-2 border-t border-slate-100 text-xs text-slate-500">
            <span>Filters applied</span>
            <button
              onClick={handleResetFilters}
              className="text-primary-600 hover:text-primary-700 font-semibold"
            >
              Clear all filters
            </button>
          </div>
        )}
      </div>

      {isError && (
        <div className="rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800 flex items-center justify-between">
          <span>Failed to load orders: {(error as any)?.message || 'Network error'}</span>
          <Button variant="outline" size="sm" onClick={() => refetch()} leftIcon={<RefreshCw className="h-3.5 w-3.5" />}>
            Retry
          </Button>
        </div>
      )}

      {/* Orders Table */}
      <div className="rounded-xl border border-slate-200 bg-white overflow-hidden shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-50/75 border-b border-slate-200 text-xs font-semibold uppercase tracking-wider text-slate-500">
              <tr>
                <th className="px-6 py-3.5">Order Number</th>
                <th className="px-6 py-3.5">Customer</th>
                <th className="px-6 py-3.5">Channel</th>
                <th className="px-6 py-3.5">Status</th>
                <th className="px-6 py-3.5">Total</th>
                <th className="px-6 py-3.5">Date</th>
                <th className="px-6 py-3.5 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {isLoading ? (
                Array.from({ length: 8 }).map((_, idx) => (
                  <TableRowSkeleton key={idx} columns={7} />
                ))
              ) : orders.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-12">
                    <EmptyState
                      title="No orders found"
                      description={
                        searchTerm || selectedStatus || startDate
                          ? 'Try adjusting your filters or search terms.'
                          : 'You haven’t created or received any orders yet.'
                      }
                      actionLabel={!searchTerm && !selectedStatus ? 'Create Order' : undefined}
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
                    <td className="px-6 py-4">
                      <div className="font-medium text-slate-900">{order.customer?.name || 'Walk-in'}</div>
                      <div className="text-xs text-slate-400">{order.customer?.phone_number || ''}</div>
                    </td>
                    <td className="px-6 py-4 text-xs">
                      <span className="capitalize px-2 py-0.5 rounded bg-slate-100 text-slate-600 font-medium">
                        {order.channel}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      <OrderStatusBadge status={order.status} />
                    </td>
                    <td className="px-6 py-4 font-semibold text-slate-900">
                      {formatCurrency(
                        order.total_amount,
                        order.currency || activeBusiness?.currency || 'USD'
                      )}
                    </td>
                    <td className="px-6 py-4 text-slate-500 whitespace-nowrap">
                      {formatDate(order.created_at, 'MMM d, yyyy h:mm a')}
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
                        <Eye className="h-4 w-4 mr-1 text-slate-400" />
                        Details
                      </Button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {total > 0 && (
          <div className="border-t border-slate-100 bg-white">
            <Pagination
              currentPage={page}
              totalPages={totalPages}
              totalItems={total}
              pageSize={pageSize}
              onPageChange={(newPage) => setPage(newPage)}
            />
          </div>
        )}
      </div>
    </div>
  )
}
export default OrdersPage
