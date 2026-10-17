import { useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { useBusinessStore } from '@/stores/businessStore'
import { Business, BusinessCreate } from '@/types'
import { useAuth } from '@/hooks/useAuth'

export function useBusiness() {
  const { isAuthenticated } = useAuth()
  const queryClient = useQueryClient()
  const { activeBusiness, businesses, setActiveBusiness, setBusinesses } = useBusinessStore()

  const {
    data: fetchedBusinesses,
    isLoading,
    isError,
    error,
    refetch,
  } = useQuery<Business[]>({
    queryKey: ['businesses'],
    queryFn: async () => {
      return api.get<Business[]>('businesses')
    },
    enabled: isAuthenticated,
    staleTime: 1000 * 60 * 5, // 5 minutes
  })

  // Sync fetched businesses with the store
  useEffect(() => {
    if (fetchedBusinesses) {
      setBusinesses(fetchedBusinesses)
    }
  }, [fetchedBusinesses, setBusinesses])

  // Mutation to create a new business
  const createBusinessMutation = useMutation({
    mutationFn: async (data: BusinessCreate) => {
      return api.post<Business>('businesses', data)
    },
    onSuccess: (newBusiness) => {
      queryClient.invalidateQueries({ queryKey: ['businesses'] })
      setActiveBusiness(newBusiness)
    },
  })

  return {
    businesses: businesses.length > 0 ? businesses : fetchedBusinesses || [],
    activeBusiness,
    setActiveBusiness,
    isLoading,
    isError,
    error,
    refetch,
    createBusiness: createBusinessMutation.mutateAsync,
    isCreating: createBusinessMutation.isPending,
  }
}
