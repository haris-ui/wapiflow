import React, { useState } from 'react'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '@/components/ui/Dialog'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Label } from '@/components/ui/Label'
import { useProducts } from '@/hooks/useProducts'
import { useQuickOrderFromConversation } from '@/hooks/useConversations'
import { Plus, Trash2, ShoppingBag } from 'lucide-react'

interface QuickOrderModalProps {
  isOpen: boolean
  onClose: () => void
  conversationId: string
  customerName?: string
}

interface OrderLineItem {
  productId: string
  quantity: number
}

export const QuickOrderModal: React.FC<QuickOrderModalProps> = ({
  isOpen,
  onClose,
  conversationId,
  customerName,
}) => {
  const { data: productsData } = useProducts({ is_active: true })
  const quickOrderMutation = useQuickOrderFromConversation(conversationId)

  const [items, setItems] = useState<OrderLineItem[]>([{ productId: '', quantity: 1 }])
  const [fulfillmentAddress, setFulfillmentAddress] = useState('')
  const [notes, setNotes] = useState('')
  const [errorMsg, setErrorMsg] = useState<string | null>(null)

  const products = productsData?.items || []

  const handleAddItem = () => {
    setItems((prev) => [...prev, { productId: '', quantity: 1 }])
  }

  const handleRemoveItem = (index: number) => {
    setItems((prev) => prev.filter((_, i) => i !== index))
  }

  const handleProductChange = (index: number, productId: string) => {
    setItems((prev) => {
      const updated = [...prev]
      updated[index].productId = productId
      return updated
    })
  }

  const handleQuantityChange = (index: number, quantity: number) => {
    setItems((prev) => {
      const updated = [...prev]
      updated[index].quantity = Math.max(1, quantity)
      return updated
    })
  }

  // Calculate estimated total
  const calculatedTotal = items.reduce((sum, item) => {
    const product = products.find((p) => p.id === item.productId)
    if (!product) return sum
    return sum + product.price * item.quantity
  }, 0)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setErrorMsg(null)

    // Validation
    const validItems = items.filter((item) => item.productId && item.quantity > 0)
    if (validItems.length === 0) {
      setErrorMsg('Please select at least one valid product.')
      return
    }

    try {
      await quickOrderMutation.mutateAsync({
        items: validItems.map((item) => ({
          product_id: item.productId,
          quantity: item.quantity,
        })),
        fulfillment_address: fulfillmentAddress.trim() || undefined,
        notes: notes.trim() || undefined,
        idempotency_key: `quick-order-${conversationId}-${Date.now()}`,
      })

      // Reset and close
      setItems([{ productId: '', quantity: 1 }])
      setFulfillmentAddress('')
      setNotes('')
      onClose()
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to create order from conversation.')
    }
  }

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-md md:max-w-lg">
        <DialogHeader>
          <div className="flex items-center gap-2">
            <div className="p-2 bg-primary-50 rounded-lg text-primary-600">
              <ShoppingBag className="h-5 w-5" />
            </div>
            <div>
              <DialogTitle>Create Quick Order</DialogTitle>
              <DialogDescription>
                Convert this WhatsApp conversation with{' '}
                <span className="font-semibold text-slate-800">{customerName || 'customer'}</span>{' '}
                into a confirmed order.
              </DialogDescription>
            </div>
          </div>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4 py-2">
          {errorMsg && (
            <div className="p-3 text-xs bg-red-50 text-red-700 border border-red-200 rounded-lg">
              {errorMsg}
            </div>
          )}

          {/* Product Items */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <Label className="text-xs font-semibold uppercase tracking-wider text-slate-600">
                Products & Quantities
              </Label>
              <button
                type="button"
                onClick={handleAddItem}
                className="text-xs font-medium text-primary-600 hover:text-primary-700 flex items-center gap-1"
              >
                <Plus className="h-3.5 w-3.5" /> Add Item
              </button>
            </div>

            {items.map((item, index) => (
              <div key={index} className="flex items-center gap-2">
                  <select
                    className="flex-1 h-9 rounded-md border border-slate-200 bg-white px-3 py-1 text-sm shadow-sm focus:outline-none focus:ring-1 focus:ring-primary-500"
                    value={item.productId}
                    onChange={(e) => handleProductChange(index, e.target.value)}
                    required
                  >
                    <option value="">Select a product...</option>
                    {products.map((p) => (
                      <option key={p.id} value={p.id}>
                        {p.name} ({p.currency} {p.price.toFixed(2)})
                      </option>
                    ))}
                  </select>

                  <Input
                    type="number"
                    min={1}
                    className="w-20 h-9"
                    value={item.quantity}
                    onChange={(e) => handleQuantityChange(index, parseInt(e.target.value, 10) || 1)}
                    required
                  />

                  {items.length > 1 && (
                    <button
                      type="button"
                      onClick={() => handleRemoveItem(index)}
                      className="p-1.5 text-slate-400 hover:text-red-500 transition-colors"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  )}
                </div>
              )
            )}
          </div>

          {/* Fulfillment Address */}
          <div className="space-y-1.5">
            <Label htmlFor="address" className="text-xs font-semibold uppercase tracking-wider text-slate-600">
              Delivery / Fulfillment Address
            </Label>
            <Input
              id="address"
              placeholder="e.g. 742 Evergreen Terrace, Springfield"
              value={fulfillmentAddress}
              onChange={(e) => setFulfillmentAddress(e.target.value)}
            />
          </div>

          {/* Notes */}
          <div className="space-y-1.5">
            <Label htmlFor="notes" className="text-xs font-semibold uppercase tracking-wider text-slate-600">
              Order Notes (Optional)
            </Label>
            <Input
              id="notes"
              placeholder="e.g. Leave package by side door, call on arrival"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
            />
          </div>

          {/* Summary */}
          <div className="p-3 bg-slate-50 rounded-lg flex items-center justify-between text-sm border border-slate-100">
            <span className="font-medium text-slate-600">Estimated Total:</span>
            <span className="text-base font-bold text-slate-900">
              ${calculatedTotal.toFixed(2)}
            </span>
          </div>

          <DialogFooter className="pt-2">
            <Button type="button" variant="outline" onClick={onClose} disabled={quickOrderMutation.isPending}>
              Cancel
            </Button>
            <Button type="submit" variant="primary" isLoading={quickOrderMutation.isPending}>
              Create & Confirm Order
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
