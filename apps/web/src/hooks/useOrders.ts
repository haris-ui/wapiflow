import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { useBusinessStore } from '@/stores/businessStore'
import {
  Order,
  OrderCreate,
  OrderStatus,
  OrderStatusUpdate,
  PaginatedResponse,
  DashboardStats,
} from '@/types'
import { generateUUID } from '@/lib/utils'

export interface OrderFilters {
  status?: OrderStatus | ''
  search?: string
  startDate?: string
  endDate?: string
  page?: number
  pageSize?: number
}

export function useOrders(filters: OrderFilters = {}) {
  const { activeBusiness } = useBusinessStore()
  const businessId = activeBusiness?.id

  return useQuery<PaginatedResponse<Order>>({
    queryKey: ['orders', businessId, filters],
    queryFn: async () => {
      if (!businessId) {
        return { items: [], total: 0, page: 1, page_size: 10, total_pages: 0 }
      }
      return api.get<PaginatedResponse<Order>>(`businesses/${businessId}/orders`, {
        businessId,
        params: {
          status: filters.status || undefined,
          search: filters.search || undefined,
          start_date: filters.startDate || undefined,
          end_date: filters.endDate || undefined,
          page: filters.page || 1,
          page_size: filters.pageSize || 10,
        },
      })
    },
    enabled: !!businessId,
  })
}

export function useOrder(orderId?: string) {
  const { activeBusiness } = useBusinessStore()
  const businessId = activeBusiness?.id

  return useQuery<Order>({
    queryKey: ['order', businessId, orderId],
    queryFn: async () => {
      if (!businessId || !orderId) throw new Error('Business and Order ID required')
      return api.get<Order>(`businesses/${businessId}/orders/${orderId}`, {
        businessId,
      })
    },
    enabled: !!businessId && !!orderId,
  })
}

export function useCreateOrder() {
  const queryClient = useQueryClient()
  const { activeBusiness } = useBusinessStore()
  const businessId = activeBusiness?.id

  return useMutation({
    mutationFn: async (orderData: OrderCreate) => {
      if (!businessId) throw new Error('No active business selected')
      const idempotencyKey = generateUUID()
      return api.post<Order>(`businesses/${businessId}/orders`, orderData, {
        businessId,
        idempotencyKey,
      })
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['orders', businessId] })
      queryClient.invalidateQueries({ queryKey: ['dashboard', businessId] })
    },
  })
}

export function useUpdateOrderStatus() {
  const queryClient = useQueryClient()
  const { activeBusiness } = useBusinessStore()
  const businessId = activeBusiness?.id

  return useMutation({
    mutationFn: async ({
      orderId,
      statusUpdate,
    }: {
      orderId: string
      statusUpdate: OrderStatusUpdate
    }) => {
      if (!businessId) throw new Error('No active business selected')
      return api.patch<Order>(
        `businesses/${businessId}/orders/${orderId}/status`,
        statusUpdate,
        {
          businessId,
        }
      )
    },
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ['orders', businessId] })
      queryClient.invalidateQueries({ queryKey: ['order', businessId, variables.orderId] })
      queryClient.invalidateQueries({ queryKey: ['dashboard', businessId] })
    },
  })
}

export function useDashboardStats() {
  const { activeBusiness } = useBusinessStore()
  const businessId = activeBusiness?.id

  return useQuery<DashboardStats>({
    queryKey: ['dashboard', businessId],
    queryFn: async () => {
      if (!businessId) {
        return {
          today_orders_count: 0,
          pending_orders_count: 0,
          today_revenue: 0,
          currency: activeBusiness?.currency || 'USD',
          recent_orders: [],
        }
      }

      try {
        // Try direct dashboard endpoint first
        return await api.get<DashboardStats>(`businesses/${businessId}/dashboard`, {
          businessId,
        })
      } catch {
        // Fallback: calculate from orders endpoint if dashboard endpoint is not yet provided by backend
        const todayIso = new Date().toISOString().split('T')[0]
        const [todayOrdersRes, pendingOrdersRes, recentOrdersRes] = await Promise.all([
          api.get<PaginatedResponse<Order>>(`businesses/${businessId}/orders`, {
            businessId,
            params: { start_date: todayIso, page_size: 100 },
          }),
          api.get<PaginatedResponse<Order>>(`businesses/${businessId}/orders`, {
            businessId,
            params: { status: 'pending', page_size: 1 },
          }),
          api.get<PaginatedResponse<Order>>(`businesses/${businessId}/orders`, {
            businessId,
            params: { page_size: 5, page: 1 },
          }),
        ])

        const todayRevenue = (todayOrdersRes.items || []).reduce(
          (sum, order) => sum + (Number(order.total_amount) || 0),
          0
        )

        return {
          today_orders_count: todayOrdersRes.total || todayOrdersRes.items?.length || 0,
          pending_orders_count: pendingOrdersRes.total || 0,
          today_revenue: todayRevenue,
          currency: activeBusiness?.currency || 'USD',
          recent_orders: recentOrdersRes.items || [],
        }
      }
    },
    enabled: !!businessId,
    refetchInterval: 1000 * 30, // 30 seconds poll
  })
}
