import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { useBusinessStore } from '@/stores/businessStore'
import { Customer, CustomerCreate, Order, PaginatedResponse } from '@/types'

export interface CustomerFilters {
  search?: string
  page?: number
  pageSize?: number
}

export function useCustomers(filters: CustomerFilters = {}) {
  const { activeBusiness } = useBusinessStore()
  const businessId = activeBusiness?.id

  return useQuery<PaginatedResponse<Customer>>({
    queryKey: ['customers', businessId, filters],
    queryFn: async () => {
      if (!businessId) {
        return { items: [], total: 0, page: 1, page_size: 10, total_pages: 0 }
      }
      const data = await api.get<any>(`businesses/${businessId}/customers`, {
        businessId,
        params: {
          search: filters.search || undefined,
          page: filters.page || 1,
          page_size: filters.pageSize || 10,
        },
      })

      if (Array.isArray(data)) {
        return {
          items: data,
          total: data.length,
          page: 1,
          page_size: data.length,
          total_pages: 1,
        }
      }
      return data
    },
    enabled: !!businessId,
  })
}

export function useCustomer(customerId?: string) {
  const { activeBusiness } = useBusinessStore()
  const businessId = activeBusiness?.id

  return useQuery<Customer>({
    queryKey: ['customer', businessId, customerId],
    queryFn: async () => {
      if (!businessId || !customerId) throw new Error('Business and Customer ID required')
      return api.get<Customer>(`businesses/${businessId}/customers/${customerId}`, {
        businessId,
      })
    },
    enabled: !!businessId && !!customerId,
  })
}

export function useCustomerOrders(customerId?: string) {
  const { activeBusiness } = useBusinessStore()
  const businessId = activeBusiness?.id

  return useQuery<Order[]>({
    queryKey: ['customerOrders', businessId, customerId],
    queryFn: async () => {
      if (!businessId || !customerId) return []
      try {
        const data = await api.get<any>(
          `businesses/${businessId}/customers/${customerId}/orders`,
          {
            businessId,
          }
        )
        return Array.isArray(data) ? data : data.items || []
      } catch {
        // Fallback: query orders with search/customer filter
        const res = await api.get<PaginatedResponse<Order>>(`businesses/${businessId}/orders`, {
          businessId,
          params: { page_size: 50 },
        })
        return (res.items || []).filter((o) => o.customer_id === customerId)
      }
    },
    enabled: !!businessId && !!customerId,
  })
}

export function useCreateCustomer() {
  const queryClient = useQueryClient()
  const { activeBusiness } = useBusinessStore()
  const businessId = activeBusiness?.id

  return useMutation({
    mutationFn: async (customerData: CustomerCreate) => {
      if (!businessId) throw new Error('No active business selected')
      return api.post<Customer>(`businesses/${businessId}/customers`, customerData, {
        businessId,
      })
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['customers', businessId] })
    },
  })
}
