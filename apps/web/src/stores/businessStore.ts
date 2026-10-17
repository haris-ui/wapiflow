import { create } from 'zustand'
import { Business } from '@/types'

const STORAGE_KEY = 'wapiflow_active_business_id'

interface BusinessState {
  activeBusiness: Business | null
  businesses: Business[]
  setActiveBusiness: (business: Business | null) => void
  setBusinesses: (businesses: Business[]) => void
}

export const useBusinessStore = create<BusinessState>((set) => ({
  activeBusiness: null,
  businesses: [],
  setActiveBusiness: (business) => {
    if (business) {
      localStorage.setItem(STORAGE_KEY, business.id)
    } else {
      localStorage.removeItem(STORAGE_KEY)
    }
    set({ activeBusiness: business })
  },
  setBusinesses: (businesses) => {
    const savedId = localStorage.getItem(STORAGE_KEY)
    let matched = businesses.find((b) => b.id === savedId)
    if (!matched && businesses.length > 0) {
      matched = businesses[0]
      localStorage.setItem(STORAGE_KEY, matched.id)
    }
    set({
      businesses,
      activeBusiness: matched || null,
    })
  },
}))
