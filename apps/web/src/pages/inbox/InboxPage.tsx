import React, { useState, useEffect, useRef } from 'react'
import {
  useConversations,
  useConversation,
  useMessages,
  useSendMessage,
  useUpdateConversationStatus,
} from '@/hooks/useConversations'
import { ConversationStatus } from '@/types'
import { QuickOrderModal } from './QuickOrderModal'
import { Input } from '@/components/ui/Input'
import { Button } from '@/components/ui/Button'
import { Badge } from '@/components/ui/Badge'
import { Spinner } from '@/components/ui/Spinner'
import {
  MessageSquare,
  Search,
  Send,
  Lock,
  ShoppingBag,
  Check,
  CheckCheck,
  AlertCircle,
  Clock,
  Settings,
} from 'lucide-react'
import { Link } from 'react-router-dom'
import { cn } from '@/lib/utils'

export default function InboxPage() {
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [statusFilter, setStatusFilter] = useState<ConversationStatus | 'all'>('open')
  const [search, setSearch] = useState('')
  const [messageText, setMessageText] = useState('')
  const [isInternalNote, setIsInternalNote] = useState(false)
  const [isOrderModalOpen, setIsOrderModalOpen] = useState(false)

  const messagesEndRef = useRef<HTMLDivElement>(null)

  // Fetch conversations list
  const {
    data: convsData,
    isLoading: isLoadingConvs,
  } = useConversations({
    status: statusFilter,
    search: search.trim() || undefined,
  })

  // Fetch active conversation detail & messages
  const { data: activeConv } = useConversation(selectedId || undefined)
  const { data: messages = [], isLoading: isLoadingMessages } = useMessages(selectedId || undefined)

  const sendMessageMutation = useSendMessage(selectedId || undefined)
  const updateStatusMutation = useUpdateConversationStatus(selectedId || undefined)

  const conversations = convsData?.items || []

  // Auto-select first conversation if none selected
  useEffect(() => {
    if (!selectedId && conversations.length > 0) {
      setSelectedId(conversations[0].id)
    }
  }, [conversations, selectedId])

  // Scroll to bottom when messages update
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!messageText.trim() || !selectedId) return

    try {
      await sendMessageMutation.mutateAsync({
        content: messageText.trim(),
        is_internal_note: isInternalNote,
      })
      setMessageText('')
    } catch (err) {
      console.error('Failed to send message:', err)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSendMessage(e)
    }
  }

  const handleStatusChange = async (newStatus: ConversationStatus) => {
    if (!selectedId) return
    try {
      await updateStatusMutation.mutateAsync(newStatus)
    } catch (err) {
      console.error('Failed to update status:', err)
    }
  }

  const formatMessageTime = (dateStr: string) => {
    try {
      const d = new Date(dateStr)
      return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    } catch {
      return ''
    }
  }

  const formatPreviewTime = (dateStr?: string | null) => {
    if (!dateStr) return ''
    try {
      const d = new Date(dateStr)
      const now = new Date()
      const diffMs = now.getTime() - d.getTime()
      const diffHours = diffMs / (1000 * 60 * 60)

      if (diffHours < 24) {
        return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      }
      return d.toLocaleDateString([], { month: 'short', day: 'numeric' })
    } catch {
      return ''
    }
  }

  return (
    <div className="flex h-[calc(100vh-4rem)] overflow-hidden bg-slate-50">
      {/* ---------------------------------------------------------------------- */}
      {/* LEFT COLUMN: Conversation List & Filters */}
      {/* ---------------------------------------------------------------------- */}
      <div className="flex w-80 md:w-96 flex-col border-r border-slate-200 bg-white">
        {/* Inbox Header */}
        <div className="p-4 border-b border-slate-100">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <MessageSquare className="h-5 w-5 text-primary-600" />
              <h1 className="font-bold text-lg text-slate-900">WhatsApp Inbox</h1>
            </div>
            <Link
              to="/settings/whatsapp"
              className="p-1.5 text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded-lg transition-colors"
              title="WhatsApp Settings"
            >
              <Settings className="h-4 w-4" />
            </Link>
          </div>

          {/* Search Box */}
          <div className="relative mb-3">
            <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
            <Input
              type="text"
              placeholder="Search conversations..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="pl-9 h-9 text-xs"
            />
          </div>

          {/* Status Tabs */}
          <div className="flex rounded-lg bg-slate-100 p-1 text-xs">
            {(['all', 'open', 'resolved', 'snoozed'] as const).map((tab) => (
              <button
                key={tab}
                onClick={() => setStatusFilter(tab)}
                className={cn(
                  'flex-1 py-1 text-center font-medium capitalize rounded-md transition-all',
                  statusFilter === tab
                    ? 'bg-white text-slate-900 shadow-sm'
                    : 'text-slate-600 hover:text-slate-900'
                )}
              >
                {tab}
              </button>
            ))}
          </div>
        </div>

        {/* Conversation Cards List */}
        <div className="flex-1 overflow-y-auto divide-y divide-slate-100">
          {isLoadingConvs ? (
            <div className="flex h-48 items-center justify-center">
              <Spinner size="md" className="text-primary-600" />
            </div>
          ) : conversations.length === 0 ? (
            <div className="p-8 text-center">
              <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-slate-100 text-slate-400 mb-3">
                <MessageSquare className="h-6 w-6" />
              </div>
              <p className="text-sm font-semibold text-slate-700">No conversations</p>
              <p className="text-xs text-slate-500 mt-1">
                Incoming WhatsApp messages will appear here in real time.
              </p>
            </div>
          ) : (
            conversations.map((conv) => {
              const isSelected = conv.id === selectedId
              const customerName = conv.customer?.name || 'Customer'
              const customerPhone = conv.customer?.phone_number || ''

              return (
                <div
                  key={conv.id}
                  onClick={() => setSelectedId(conv.id)}
                  className={cn(
                    'p-3.5 cursor-pointer transition-colors relative flex items-start gap-3',
                    isSelected
                      ? 'bg-primary-50/60 border-l-4 border-primary-600'
                      : 'hover:bg-slate-50/80'
                  )}
                >
                  {/* Avatar */}
                  <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-primary-100 text-primary-700 font-semibold text-sm">
                    {customerName.charAt(0).toUpperCase()}
                  </div>

                  {/* Body */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between mb-0.5">
                      <span className="font-semibold text-sm text-slate-900 truncate">
                        {customerName}
                      </span>
                      <span className="text-[11px] text-slate-400 shrink-0">
                        {formatPreviewTime(conv.last_message_at)}
                      </span>
                    </div>

                    <div className="flex items-center justify-between">
                      <p className="text-xs text-slate-500 truncate max-w-[180px]">
                        {conv.last_message_preview || customerPhone || 'Active conversation'}
                      </p>

                      {conv.unread_count > 0 && (
                        <span className="ml-2 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-primary-600 text-[11px] font-bold text-white">
                          {conv.unread_count}
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              )
            })
          )}
        </div>
      </div>

      {/* ---------------------------------------------------------------------- */}
      {/* RIGHT COLUMN: Active Chat Thread */}
      {/* ---------------------------------------------------------------------- */}
      <div className="flex flex-1 flex-col bg-slate-100 overflow-hidden">
        {selectedId && activeConv ? (
          <>
            {/* Thread Header */}
            <div className="flex h-16 shrink-0 items-center justify-between border-b border-slate-200 bg-white px-6 shadow-sm">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-full bg-primary-100 text-primary-700 font-bold text-sm">
                  {(activeConv.customer?.name || 'C').charAt(0).toUpperCase()}
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <h2 className="font-bold text-slate-900 text-sm">
                      {activeConv.customer?.name || 'WhatsApp Customer'}
                    </h2>
                    <Badge
                      variant={
                        activeConv.status === 'open'
                          ? 'delivered'
                          : activeConv.status === 'snoozed'
                          ? 'pending'
                          : 'ready'
                      }
                    >
                      {activeConv.status}
                    </Badge>
                  </div>
                  <p className="text-xs text-slate-500">
                    {activeConv.customer?.phone_number || 'Direct chat'}
                  </p>
                </div>
              </div>

              {/* Actions Header */}
              <div className="flex items-center gap-2.5">
                {/* Status Switcher */}
                <select
                  value={activeConv.status}
                  onChange={(e) => handleStatusChange(e.target.value as ConversationStatus)}
                  className="h-8 rounded-md border border-slate-200 bg-white px-2.5 py-1 text-xs font-medium text-slate-700 shadow-sm focus:outline-none focus:ring-1 focus:ring-primary-500"
                >
                  <option value="open">🟢 Open</option>
                  <option value="snoozed">🟡 Snoozed</option>
                  <option value="resolved">⚪ Resolved</option>
                </select>

                {/* Quick Order Button */}
                <Button
                  size="sm"
                  variant="primary"
                  onClick={() => setIsOrderModalOpen(true)}
                  className="flex items-center gap-1.5"
                >
                  <ShoppingBag className="h-4 w-4" />
                  <span>Create Order</span>
                </Button>
              </div>
            </div>

            {/* Messages Scroll Area */}
            <div className="flex-1 overflow-y-auto p-4 md:p-6 space-y-4">
              {isLoadingMessages ? (
                <div className="flex h-full items-center justify-center">
                  <Spinner size="lg" className="text-primary-600" />
                </div>
              ) : messages.length === 0 ? (
                <div className="flex h-full items-center justify-center text-slate-400 text-sm">
                  No messages in this conversation thread yet.
                </div>
              ) : (
                messages.map((msg) => {
                  if (msg.is_internal_note) {
                    return (
                      <div key={msg.id} className="flex justify-center my-2">
                        <div className="max-w-md rounded-xl bg-amber-50 border border-amber-200/80 px-4 py-2.5 text-xs text-amber-900 shadow-sm">
                          <div className="flex items-center gap-1.5 font-semibold text-amber-800 mb-1">
                            <Lock className="h-3.5 w-3.5 text-amber-600" />
                            <span>Internal Team Note</span>
                            <span className="text-[10px] font-normal text-amber-600 ml-auto">
                              {formatMessageTime(msg.created_at)}
                            </span>
                          </div>
                          <p className="whitespace-pre-wrap">{msg.content}</p>
                        </div>
                      </div>
                    )
                  }

                  const isInbound = msg.direction === 'inbound'

                  return (
                    <div
                      key={msg.id}
                      className={cn('flex', isInbound ? 'justify-start' : 'justify-end')}
                    >
                      <div
                        className={cn(
                          'max-w-[75%] rounded-2xl px-4 py-2.5 shadow-sm text-sm',
                          isInbound
                            ? 'bg-white text-slate-800 rounded-tl-sm border border-slate-200/80'
                            : 'bg-primary-600 text-white rounded-tr-sm'
                        )}
                      >
                        <p className="whitespace-pre-wrap break-words leading-relaxed">
                          {msg.content}
                        </p>
                        <div
                          className={cn(
                            'mt-1 flex items-center justify-end gap-1 text-[10px]',
                            isInbound ? 'text-slate-400' : 'text-primary-200'
                          )}
                        >
                          <span>{formatMessageTime(msg.created_at)}</span>
                          {!isInbound && (
                            <span>
                              {msg.status === 'read' ? (
                                <CheckCheck className="h-3 w-3 text-cyan-300" />
                              ) : msg.status === 'delivered' ? (
                                <CheckCheck className="h-3 w-3" />
                              ) : msg.status === 'sent' ? (
                                <Check className="h-3 w-3" />
                              ) : msg.status === 'failed' ? (
                                <AlertCircle className="h-3 w-3 text-red-300" />
                              ) : (
                                <Clock className="h-3 w-3" />
                              )}
                            </span>
                          )}
                        </div>
                      </div>
                    </div>
                  )
                })
              )}
              <div ref={messagesEndRef} />
            </div>

            {/* Message Input Box */}
            <div className="border-t border-slate-200 bg-white p-4">
              <form onSubmit={handleSendMessage} className="space-y-2">
                {/* Mode Selector (WhatsApp Message vs Internal Note) */}
                <div className="flex items-center justify-between text-xs px-1">
                  <div className="flex items-center gap-3">
                    <button
                      type="button"
                      onClick={() => setIsInternalNote(false)}
                      className={cn(
                        'flex items-center gap-1.5 font-medium px-2 py-1 rounded transition-colors',
                        !isInternalNote
                          ? 'bg-primary-50 text-primary-700'
                          : 'text-slate-500 hover:text-slate-800'
                      )}
                    >
                      <MessageSquare className="h-3.5 w-3.5" />
                      <span>WhatsApp Message</span>
                    </button>
                    <button
                      type="button"
                      onClick={() => setIsInternalNote(true)}
                      className={cn(
                        'flex items-center gap-1.5 font-medium px-2 py-1 rounded transition-colors',
                        isInternalNote
                          ? 'bg-amber-100 text-amber-800'
                          : 'text-slate-500 hover:text-slate-800'
                      )}
                    >
                      <Lock className="h-3.5 w-3.5" />
                      <span>Internal Note (Private)</span>
                    </button>
                  </div>

                  <span className="text-[11px] text-slate-400 hidden sm:inline">
                    Press <kbd className="px-1 py-0.5 bg-slate-100 rounded text-slate-600">Enter</kbd> to send, <kbd className="px-1 py-0.5 bg-slate-100 rounded text-slate-600">Shift+Enter</kbd> for newline
                  </span>
                </div>

                <div className="flex items-end gap-2">
                  <textarea
                    rows={2}
                    value={messageText}
                    onChange={(e) => setMessageText(e.target.value)}
                    onKeyDown={handleKeyDown}
                    placeholder={
                      isInternalNote
                        ? 'Type private note for team members...'
                        : 'Type message to send via WhatsApp...'
                    }
                    className={cn(
                      'flex-1 resize-none rounded-xl border p-2.5 text-sm shadow-sm focus:outline-none focus:ring-2',
                      isInternalNote
                        ? 'border-amber-300 bg-amber-50/30 focus:border-amber-500 focus:ring-amber-400'
                        : 'border-slate-200 focus:border-primary-500 focus:ring-primary-400'
                    )}
                  />

                  <Button
                    type="submit"
                    variant={isInternalNote ? 'secondary' : 'primary'}
                    disabled={!messageText.trim() || sendMessageMutation.isPending}
                    className="h-10 px-4 shrink-0 rounded-xl"
                  >
                    {sendMessageMutation.isPending ? (
                      <Spinner size="sm" />
                    ) : (
                      <Send className="h-4 w-4" />
                    )}
                  </Button>
                </div>
              </form>
            </div>
          </>
        ) : (
          <div className="flex h-full flex-col items-center justify-center p-8 text-center">
            <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-primary-50 text-primary-600 mb-4 shadow-sm">
              <MessageSquare className="h-8 w-8" />
            </div>
            <h3 className="font-bold text-lg text-slate-800">No Conversation Selected</h3>
            <p className="text-sm text-slate-500 max-w-sm mt-1">
              Select a conversation from the left to view customer chat history, send WhatsApp replies, or create quick orders.
            </p>
          </div>
        )}
      </div>

      {/* Quick Order Modal */}
      {selectedId && (
        <QuickOrderModal
          isOpen={isOrderModalOpen}
          onClose={() => setIsOrderModalOpen(false)}
          conversationId={selectedId}
          customerName={activeConv?.customer?.name}
        />
      )}
    </div>
  )
}
