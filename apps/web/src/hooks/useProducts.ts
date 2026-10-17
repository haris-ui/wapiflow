import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { useBusinessStore } from '@/stores/businessStore'
import { Product, ProductCreate, ProductUpdate, PaginatedResponse } from '@/types'

export interface ProductFilters {
  search?: string
  category?: string
  is_active?: boolean | null
  page?: number
  pageSize?: number
}

export function useProducts(filters: ProductFilters = {}) {
  const { activeBusiness } = useBusinessStore()
  const businessId = activeBusiness?.id

  return useQuery<PaginatedResponse<Product>>({
    queryKey: ['products', businessId, filters],
    queryFn: async () => {
      if (!businessId) {
        return { items: [], total: 0, page: 1, page_size: 10, total_pages: 0 }
      }
      const data = await api.get<any>(`businesses/${businessId}/products`, {
        businessId,
        params: {
          search: filters.search || undefined,
          category: filters.category || undefined,
          is_active: filters.is_active !== null ? filters.is_active : undefined,
          page: filters.page || 1,
          page_size: filters.pageSize || 10,
        },
      })

      // Normalize if backend returns array or paginated object
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

export function useProduct(productId?: string) {
  const { activeBusiness } = useBusinessStore()
  const businessId = activeBusiness?.id

  return useQuery<Product>({
    queryKey: ['product', businessId, productId],
    queryFn: async () => {
      if (!businessId || !productId) throw new Error('Business and Product ID required')
      return api.get<Product>(`businesses/${businessId}/products/${productId}`, {
        businessId,
      })
    },
    enabled: !!businessId && !!productId && productId !== 'new',
  })
}

export function useCreateProduct() {
  const queryClient = useQueryClient()
  const { activeBusiness } = useBusinessStore()
  const businessId = activeBusiness?.id

  return useMutation({
    mutationFn: async (productData: ProductCreate) => {
      if (!businessId) throw new Error('No active business selected')
      return api.post<Product>(`businesses/${businessId}/products`, productData, {
        businessId,
      })
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['products', businessId] })
    },
  })
}

export function useUpdateProduct() {
  const queryClient = useQueryClient()
  const { activeBusiness } = useBusinessStore()
  const businessId = activeBusiness?.id

  return useMutation({
    mutationFn: async ({
      productId,
      productData,
    }: {
      productId: string
      productData: ProductUpdate
    }) => {
      if (!businessId) throw new Error('No active business selected')
      return api.patch<Product>(`businesses/${businessId}/products/${productId}`, productData, {
        businessId,
      })
    },
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ['products', businessId] })
      queryClient.invalidateQueries({ queryKey: ['product', businessId, variables.productId] })
    },
  })
}

export function useDeleteProduct() {
  const queryClient = useQueryClient()
  const { activeBusiness } = useBusinessStore()
  const businessId = activeBusiness?.id

  return useMutation({
    mutationFn: async (productId: string) => {
      if (!businessId) throw new Error('No active business selected')
      return api.delete(`businesses/${businessId}/products/${productId}`, {
        businessId,
      })
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['products', businessId] })
    },
  })
}
