import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Plus, Trash2, ShoppingCart, User, AlertCircle } from 'lucide-react'
import { useBusiness } from '@/hooks/useBusiness'
import { useCreateOrder } from '@/hooks/useOrders'
import { useProducts } from '@/hooks/useProducts'
import { useCustomers } from '@/hooks/useCustomers'
import { PageHeader } from '@/components/shared/PageHeader'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Label } from '@/components/ui/Label'
import { Select } from '@/components/ui/Select'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card'
import { useToast } from '@/components/ui/Toast'
import { formatCurrency } from '@/lib/utils'
import { OrderChannel, Product } from '@/types'

interface OrderLineItem {
  product: Product
  quantity: number
  unit_price: number
}

export const CreateOrderPage: React.FC = () => {
  const navigate = useNavigate()
  const { toast } = useToast()
  const { activeBusiness } = useBusiness()

  const { data: productsData } = useProducts({ pageSize: 100, is_active: true })
  const { data: customersData } = useCustomers({ pageSize: 100 })
  const createOrderMutation = useCreateOrder()

  const [selectedCustomerId, setSelectedCustomerId] = useState<string>('')
  const [channel, setChannel] = useState<OrderChannel>('manual')
  const [lineItems, setLineItems] = useState<OrderLineItem[]>([])
  const [selectedProductId, setSelectedProductId] = useState<string>('')
  const [selectedQuantity, setSelectedQuantity] = useState<number>(1)

  const [shippingFee, setShippingFee] = useState<number>(0)
  const [discount, setDiscount] = useState<number>(0)
  const [tax, setTax] = useState<number>(0)
  const [notes, setNotes] = useState<string>('')
  const [errorMsg, setErrorMsg] = useState<string | null>(null)

  const products = productsData?.items || []
  const customers = customersData?.items || []
  const currency = activeBusiness?.currency || 'USD'

  const handleAddProduct = () => {
    if (!selectedProductId) return
    const prod = products.find((p) => p.id === selectedProductId)
    if (!prod) return

    const existingIndex = lineItems.findIndex((item) => item.product.id === prod.id)
    if (existingIndex > -1) {
      const updated = [...lineItems]
      updated[existingIndex].quantity += selectedQuantity
      setLineItems(updated)
    } else {
      setLineItems([
        ...lineItems,
        {
          product: prod,
          quantity: selectedQuantity,
          unit_price: prod.price,
        },
      ])
    }

    setSelectedProductId('')
    setSelectedQuantity(1)
  }

  const handleRemoveItem = (index: number) => {
    setLineItems(lineItems.filter((_, idx) => idx !== index))
  }

  const handleUpdateQuantity = (index: number, quantity: number) => {
    if (quantity <= 0) return
    const updated = [...lineItems]
    updated[index].quantity = quantity
    setLineItems(updated)
  }

  // Calculate subtotals
  const subtotal = lineItems.reduce(
    (sum, item) => sum + item.unit_price * item.quantity,
    0
  )
  const totalAmount = Math.max(0, subtotal + shippingFee + tax - discount)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setErrorMsg(null)

    if (!selectedCustomerId) {
      setErrorMsg('Please select a customer for this order.')
      return
    }

    if (lineItems.length === 0) {
      setErrorMsg('Please add at least one product item to the order.')
      return
    }

    try {
      const newOrder = await createOrderMutation.mutateAsync({
        customer_id: selectedCustomerId,
        channel,
        items: lineItems.map((item) => ({
          product_id: item.product.id,
          quantity: item.quantity,
          unit_price: item.unit_price,
        })),
        shipping_fee: Number(shippingFee) || 0,
        discount: Number(discount) || 0,
        tax: Number(tax) || 0,
        notes: notes || undefined,
      })

      toast({
        title: 'Order created',
        description: `Order #${newOrder.order_number} has been placed successfully.`,
        type: 'success',
      })

      navigate(`/orders/${newOrder.id}`)
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to create order. Please try again.')
    }
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Create New Order"
        description="Manually record an order placed via phone, direct message, or walk-in."
        backUrl="/orders"
        backLabel="Back to Orders"
      />

      {errorMsg && (
        <div className="flex items-center gap-2.5 rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800">
          <AlertCircle className="h-5 w-5 flex-shrink-0 text-rose-600" />
          <span>{errorMsg}</span>
        </div>
      )}

      <form onSubmit={handleSubmit}>
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Main Items & Customer Form */}
          <div className="lg:col-span-2 space-y-6">
            {/* Customer & Channel Card */}
            <Card>
              <CardHeader>
                <CardTitle className="text-base font-semibold flex items-center gap-2">
                  <User className="h-4 w-4 text-slate-500" />
                  Customer & Channel
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div>
                    <Label htmlFor="customer" required>
                      Select Customer
                    </Label>
                    <div className="mt-1.5">
                      <Select
                        id="customer"
                        value={selectedCustomerId}
                        onChange={(e) => setSelectedCustomerId(e.target.value)}
                      >
                        <option value="">-- Choose a customer --</option>
                        {customers.map((c) => (
                          <option key={c.id} value={c.id}>
                            {c.name} ({c.phone_number})
                          </option>
                        ))}
                      </Select>
                    </div>
                  </div>

                  <div>
                    <Label htmlFor="channel" required>
                      Order Channel
                    </Label>
                    <div className="mt-1.5">
                      <Select
                        id="channel"
                        value={channel}
                        onChange={(e) => setChannel(e.target.value as OrderChannel)}
                      >
                        <option value="manual">Manual Entry / Phone</option>
                        <option value="whatsapp">WhatsApp Direct</option>
                      </Select>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Line Items Card */}
            <Card>
              <CardHeader>
                <CardTitle className="text-base font-semibold flex items-center gap-2">
                  <ShoppingCart className="h-4 w-4 text-slate-500" />
                  Order Items
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-6">
                {/* Product Selector */}
                <div className="flex flex-col sm:flex-row items-end gap-3 rounded-lg bg-slate-50 p-4 border border-slate-200">
                  <div className="w-full sm:flex-1">
                    <Label htmlFor="product-select">Product</Label>
                    <div className="mt-1">
                      <Select
                        id="product-select"
                        value={selectedProductId}
                        onChange={(e) => setSelectedProductId(e.target.value)}
                      >
                        <option value="">-- Select product to add --</option>
                        {products.map((p) => (
                          <option key={p.id} value={p.id}>
                            {p.name} — {formatCurrency(p.price, p.currency || currency)} (Stock:{' '}
                            {p.stock_quantity})
                          </option>
                        ))}
                      </Select>
                    </div>
                  </div>

                  <div className="w-full sm:w-24">
                    <Label htmlFor="quantity">Qty</Label>
                    <div className="mt-1">
                      <Input
                        id="quantity"
                        type="number"
                        min="1"
                        value={selectedQuantity}
                        onChange={(e) => setSelectedQuantity(Math.max(1, parseInt(e.target.value) || 1))}
                      />
                    </div>
                  </div>

                  <Button
                    type="button"
                    variant="secondary"
                    onClick={handleAddProduct}
                    disabled={!selectedProductId}
                    leftIcon={<Plus className="h-4 w-4" />}
                    className="w-full sm:w-auto"
                  >
                    Add
                  </Button>
                </div>

                {/* Items Table */}
                <div className="divide-y divide-slate-100 border rounded-lg border-slate-200 overflow-hidden">
                  {lineItems.length === 0 ? (
                    <div className="p-8 text-center text-sm text-slate-500">
                      No products added to this order yet.
                    </div>
                  ) : (
                    lineItems.map((item, idx) => (
                      <div key={idx} className="flex items-center justify-between p-4 bg-white">
                        <div className="flex-1">
                          <p className="font-medium text-slate-900">{item.product.name}</p>
                          <p className="text-xs text-slate-500">
                            {formatCurrency(item.unit_price, currency)} each
                          </p>
                        </div>
                        <div className="flex items-center gap-4">
                          <div className="w-20">
                            <Input
                              type="number"
                              min="1"
                              value={item.quantity}
                              onChange={(e) =>
                                handleUpdateQuantity(idx, parseInt(e.target.value) || 1)
                              }
                            />
                          </div>
                          <div className="w-24 text-right font-semibold text-slate-900">
                            {formatCurrency(item.unit_price * item.quantity, currency)}
                          </div>
                          <button
                            type="button"
                            onClick={() => handleRemoveItem(idx)}
                            className="p-1.5 text-slate-400 hover:text-rose-600 transition-colors"
                          >
                            <Trash2 className="h-4 w-4" />
                          </button>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </CardContent>
            </Card>

            {/* Notes Card */}
            <Card>
              <CardHeader>
                <CardTitle className="text-base font-semibold">Special Instructions / Notes</CardTitle>
              </CardHeader>
              <CardContent>
                <textarea
                  rows={3}
                  className="w-full rounded-lg border border-slate-300 p-3 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500"
                  placeholder="e.g. Leave package by the front door, call on delivery..."
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                />
              </CardContent>
            </Card>
          </div>

          {/* Right Column: Totals & Submit */}
          <div className="space-y-6">
            <Card>
              <CardHeader className="border-b border-slate-100">
                <CardTitle className="text-base font-semibold">Order Summary</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4 pt-4">
                <div className="flex justify-between text-sm text-slate-600">
                  <span>Subtotal ({lineItems.reduce((acc, i) => acc + i.quantity, 0)} items)</span>
                  <span className="font-semibold text-slate-900">
                    {formatCurrency(subtotal, currency)}
                  </span>
                </div>

                <div className="space-y-3 pt-3 border-t border-slate-100">
                  <div>
                    <Label htmlFor="shipping" className="text-xs">
                      Shipping Fee
                    </Label>
                    <div className="mt-1">
                      <Input
                        id="shipping"
                        type="number"
                        step="0.01"
                        min="0"
                        value={shippingFee || ''}
                        placeholder="0.00"
                        onChange={(e) => setShippingFee(parseFloat(e.target.value) || 0)}
                      />
                    </div>
                  </div>

                  <div>
                    <Label htmlFor="tax" className="text-xs">
                      Tax
                    </Label>
                    <div className="mt-1">
                      <Input
                        id="tax"
                        type="number"
                        step="0.01"
                        min="0"
                        value={tax || ''}
                        placeholder="0.00"
                        onChange={(e) => setTax(parseFloat(e.target.value) || 0)}
                      />
                    </div>
                  </div>

                  <div>
                    <Label htmlFor="discount" className="text-xs">
                      Discount
                    </Label>
                    <div className="mt-1">
                      <Input
                        id="discount"
                        type="number"
                        step="0.01"
                        min="0"
                        value={discount || ''}
                        placeholder="0.00"
                        onChange={(e) => setDiscount(parseFloat(e.target.value) || 0)}
                      />
                    </div>
                  </div>
                </div>

                <div className="pt-4 border-t border-slate-200">
                  <div className="flex justify-between text-lg font-bold text-slate-900 mb-6">
                    <span>Total Amount</span>
                    <span className="text-primary-700">
                      {formatCurrency(totalAmount, currency)}
                    </span>
                  </div>

                  <Button
                    type="submit"
                    size="lg"
                    className="w-full"
                    isLoading={createOrderMutation.isPending}
                    disabled={lineItems.length === 0 || !selectedCustomerId}
                  >
                    Confirm & Create Order
                  </Button>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </form>
    </div>
  )
}
export default CreateOrderPage
