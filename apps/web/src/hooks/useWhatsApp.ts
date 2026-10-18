import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { useBusinessStore } from '@/stores/businessStore'
import { WhatsAppAccount, WhatsAppAccountConnect, WhatsAppConfigInfo } from '@/types'

export function useWhatsAppConfig() {
  const { activeBusiness } = useBusinessStore()
  const businessId = activeBusiness?.id

  return useQuery<WhatsAppConfigInfo>({
    queryKey: ['whatsapp-config', businessId],
    queryFn: async () => {
      if (!businessId) {
        return {
          status: 'disconnected',
          waba_id: null,
          app_id: null,
          webhook_url: '',
          verify_token: '',
          phone_numbers: [],
        }
      }
      return api.get<WhatsAppConfigInfo>(`businesses/${businessId}/whatsapp/config`, {
        businessId,
      })
    },
    enabled: !!businessId,
  })
}

export function useConnectWhatsApp() {
  const { activeBusiness } = useBusinessStore()
  const businessId = activeBusiness?.id
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (payload: WhatsAppAccountConnect) => {
      if (!businessId) throw new Error('Active business required')
      return api.post<WhatsAppAccount>(`businesses/${businessId}/whatsapp/connect`, payload, {
        businessId,
      })
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['whatsapp-config', businessId] })
    },
  })
}

export function useDisconnectWhatsApp() {
  const { activeBusiness } = useBusinessStore()
  const businessId = activeBusiness?.id
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async () => {
      if (!businessId) throw new Error('Active business required')
      return api.post<{ status: string; message: string }>(
        `businesses/${businessId}/whatsapp/disconnect`,
        {},
        { businessId }
      )
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['whatsapp-config', businessId] })
    },
  })
}

export function useSendTestMessage() {
  const { activeBusiness } = useBusinessStore()
  const businessId = activeBusiness?.id

  return useMutation({
    mutationFn: async (payload: { to_phone: string; message_text: string }) => {
      if (!businessId) throw new Error('Active business required')
      return api.post<{ status: string; response: any }>(
        `businesses/${businessId}/whatsapp/test-message`,
        payload,
        { businessId }
      )
    },
  })
}
