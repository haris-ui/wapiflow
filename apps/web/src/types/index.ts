/**
 * WapiFlow Core TypeScript Type Definitions
 */

export type OrderStatus =
  | 'pending'
  | 'confirmed'
  | 'preparing'
  | 'ready'
  | 'shipped'
  | 'delivered'
  | 'cancelled'

export type OrderChannel = 'manual' | 'whatsapp'

export interface User {
  id: string
  email: string
  created_at: string
  user_metadata?: {
    full_name?: string
    avatar_url?: string
  }
}

export interface Profile {
  id: string
  email: string
  full_name: string
  avatar_url?: string | null
  created_at: string
  updated_at: string
}

export interface Business {
  id: string
  name: string
  slug: string
  email?: string | null
  phone_number?: string | null
  currency: string
  timezone: string
  created_at: string
  updated_at: string
  role?: string
}

export interface BusinessMember {
  id: string
  business_id: string
  user_id: string
  role: 'owner' | 'admin' | 'member'
  created_at: string
  user?: Profile
}

export interface BusinessCreate {
  name: string
  email?: string
  phone_number?: string
  currency: string
  timezone: string
}

export interface Product {
  id: string
  business_id: string
  name: string
  description?: string | null
  sku?: string | null
  price: number
  currency: string
  stock_quantity: number
  low_stock_threshold?: number | null
  category?: string | null
  image_url?: string | null
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface ProductCreate {
  name: string
  description?: string
  sku?: string
  price: number
  currency?: string
  stock_quantity: number
  low_stock_threshold?: number
  category?: string
  image_url?: string
  is_active?: boolean
}

export interface ProductUpdate {
  name?: string
  description?: string
  sku?: string
  price?: number
  currency?: string
  stock_quantity?: number
  low_stock_threshold?: number
  category?: string
  image_url?: string
  is_active?: boolean
}

export interface Customer {
  id: string
  business_id: string
  name: string
  phone_number: string
  email?: string | null
  address?: string | null
  city?: string | null
  notes?: string | null
  total_orders?: number
  total_spent?: number
  created_at: string
  updated_at: string
}

export interface CustomerCreate {
  name: string
  phone_number: string
  email?: string
  address?: string
  city?: string
  notes?: string
}

export interface OrderItem {
  id?: string
  order_id?: string
  product_id: string
  product_name: string
  unit_price: number
  quantity: number
  total_price: number
  product?: Product
}

export interface OrderStatusHistoryItem {
  id: string
  order_id: string
  status: OrderStatus
  comment?: string | null
  created_at: string
  created_by?: string | null
}

export interface Order {
  id: string
  order_number: string
  business_id: string
  customer_id: string
  customer: Customer
  status: OrderStatus
  channel: OrderChannel
  subtotal: number
  tax: number
  shipping_fee: number
  discount: number
  total_amount: number
  currency: string
  notes?: string | null
  created_at: string
  updated_at: string
  items: OrderItem[]
  history?: OrderStatusHistoryItem[]
}

export interface OrderCreateItem {
  product_id: string
  quantity: number
  unit_price?: number
}

export interface OrderCreate {
  customer_id: string
  channel: OrderChannel
  items: OrderCreateItem[]
  shipping_fee?: number
  discount?: number
  tax?: number
  notes?: string
}

export interface OrderStatusUpdate {
  status: OrderStatus
  comment?: string
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

export interface DashboardStats {
  today_orders_count: number
  pending_orders_count: number
  today_revenue: number
  currency: string
  recent_orders: Order[]
}

export class ApiError extends Error {
  status: number
  code?: string
  details?: unknown

  constructor(message: string, status: number, code?: string, details?: unknown) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
    this.details = details
  }
}

// ==============================================================================
// Phase 2: WhatsApp & Conversation Types
// ==============================================================================

export interface WhatsAppPhoneNumber {
  id: string
  business_id: string
  whatsapp_account_id: string
  phone_number: string
  display_name?: string | null
  quality_rating?: string | null
  status: string
  is_primary: boolean
  created_at: string
}

export interface WhatsAppAccount {
  id: string
  business_id: string
  waba_id: string
  app_id: string
  status: 'connected' | 'disconnected' | 'error'
  webhook_verified_at?: string | null
  created_at: string
  updated_at: string
  phone_numbers?: WhatsAppPhoneNumber[]
}

export interface WhatsAppConfigInfo {
  status: 'connected' | 'disconnected' | 'error'
  waba_id?: string | null
  app_id?: string | null
  webhook_url: string
  verify_token: string
  phone_numbers: WhatsAppPhoneNumber[]
}

export interface WhatsAppAccountConnect {
  waba_id: string
  app_id: string
  access_token: string
  phone_numbers?: Array<{
    phone_number: string
    display_name?: string
    is_primary?: boolean
  }>
}

export type MessageType =
  | 'text'
  | 'image'
  | 'audio'
  | 'video'
  | 'document'
  | 'template'
  | 'interactive'
  | 'unknown'

export type MessageStatus = 'pending' | 'sent' | 'delivered' | 'read' | 'failed'

export interface Message {
  id: string
  conversation_id: string
  business_id: string
  wa_message_id?: string | null
  direction: 'inbound' | 'outbound'
  message_type: MessageType
  content?: string | null
  media_url?: string | null
  media_mime_type?: string | null
  status: MessageStatus
  error_code?: string | null
  error_message?: string | null
  sent_by?: string | null
  is_internal_note: boolean
  metadata?: Record<string, any> | null
  created_at: string
  updated_at: string
}

export type ConversationStatus = 'open' | 'resolved' | 'snoozed'

export interface Conversation {
  id: string
  business_id: string
  customer_id?: string | null
  customer?: Customer | null
  whatsapp_phone_number_id?: string | null
  wa_conversation_id?: string | null
  status: ConversationStatus
  assigned_to?: string | null
  unread_count: number
  last_message_at?: string | null
  last_message_preview?: string | null
  created_at: string
  updated_at: string
}

export interface ConversationDetail extends Conversation {
  messages: Message[]
}

export interface MessageCreate {
  content: string
  is_internal_note?: boolean
  message_type?: string
}

export interface ConversationQuickOrderCreate {
  items: Array<{ product_id: string; quantity: number }>
  notes?: string
  fulfillment_address?: string
  idempotency_key?: string
}

