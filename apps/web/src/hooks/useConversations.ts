import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { useBusinessStore } from '@/stores/businessStore'
import {
  Conversation,
  ConversationDetail,
  ConversationQuickOrderCreate,
  ConversationStatus,
  Message,
  MessageCreate,
  Order,
  PaginatedResponse,
} from '@/types'

export interface ConversationFilters {
  status?: ConversationStatus | 'all'
  search?: string
  page?: number
  pageSize?: number
}

export function useConversations(filters: ConversationFilters = {}) {
  const { activeBusiness } = useBusinessStore()
  const businessId = activeBusiness?.id

  return useQuery<PaginatedResponse<Conversation>>({
    queryKey: ['conversations', businessId, filters],
    queryFn: async () => {
      if (!businessId) {
        return { items: [], total: 0, page: 1, page_size: 20, total_pages: 0 }
      }
      return api.get<PaginatedResponse<Conversation>>(
        `businesses/${businessId}/conversations`,
        {
          businessId,
          params: {
            status: filters.status && filters.status !== 'all' ? filters.status : undefined,
            search: filters.search || undefined,
            page: filters.page || 1,
            page_size: filters.pageSize || 20,
          },
        }
      )
    },
    enabled: !!businessId,
    refetchInterval: 5000, // Poll every 5s for fresh incoming WhatsApp messages
  })
}

export function useConversation(conversationId?: string) {
  const { activeBusiness } = useBusinessStore()
  const businessId = activeBusiness?.id

  return useQuery<ConversationDetail>({
    queryKey: ['conversation', businessId, conversationId],
    queryFn: async () => {
      if (!businessId || !conversationId) throw new Error('Business and Conversation ID required')
      return api.get<ConversationDetail>(
        `businesses/${businessId}/conversations/${conversationId}`,
        { businessId }
      )
    },
    enabled: !!businessId && !!conversationId,
  })
}

export function useMessages(conversationId?: string) {
  const { activeBusiness } = useBusinessStore()
  const businessId = activeBusiness?.id

  return useQuery<Message[]>({
    queryKey: ['messages', businessId, conversationId],
    queryFn: async () => {
      if (!businessId || !conversationId) return []
      return api.get<Message[]>(
        `businesses/${businessId}/conversations/${conversationId}/messages`,
        { businessId }
      )
    },
    enabled: !!businessId && !!conversationId,
    refetchInterval: 3000, // Poll active chat thread every 3s
  })
}

export function useSendMessage(conversationId?: string) {
  const { activeBusiness } = useBusinessStore()
  const businessId = activeBusiness?.id
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (payload: MessageCreate) => {
      if (!businessId || !conversationId) throw new Error('Business and Conversation ID required')
      return api.post<Message>(
        `businesses/${businessId}/conversations/${conversationId}/messages`,
        payload,
        { businessId }
      )
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['messages', businessId, conversationId] })
      queryClient.invalidateQueries({ queryKey: ['conversation', businessId, conversationId] })
      queryClient.invalidateQueries({ queryKey: ['conversations', businessId] })
    },
  })
}

export function useUpdateConversationStatus(conversationId?: string) {
  const { activeBusiness } = useBusinessStore()
  const businessId = activeBusiness?.id
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (status: ConversationStatus) => {
      if (!businessId || !conversationId) throw new Error('Business and Conversation ID required')
      return api.patch<Conversation>(
        `businesses/${businessId}/conversations/${conversationId}`,
        { status },
        { businessId }
      )
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['conversation', businessId, conversationId] })
      queryClient.invalidateQueries({ queryKey: ['conversations', businessId] })
    },
  })
}

export function useQuickOrderFromConversation(conversationId?: string) {
  const { activeBusiness } = useBusinessStore()
  const businessId = activeBusiness?.id
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (payload: ConversationQuickOrderCreate) => {
      if (!businessId || !conversationId) throw new Error('Business and Conversation ID required')
      return api.post<Order>(
        `businesses/${businessId}/conversations/${conversationId}/orders`,
        payload,
        { businessId }
      )
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['messages', businessId, conversationId] })
      queryClient.invalidateQueries({ queryKey: ['orders', businessId] })
      queryClient.invalidateQueries({ queryKey: ['conversations', businessId] })
    },
  })
}
