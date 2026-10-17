import React, { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { AlertCircle } from 'lucide-react'
import { useProduct, useCreateProduct, useUpdateProduct } from '@/hooks/useProducts'
import { useBusiness } from '@/hooks/useBusiness'
import { PageHeader } from '@/components/shared/PageHeader'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Label } from '@/components/ui/Label'
import { Select } from '@/components/ui/Select'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card'
import { Skeleton } from '@/components/ui/Skeleton'
import { useToast } from '@/components/ui/Toast'
import { CURRENCIES } from '@/lib/constants'

const productFormSchema = z.object({
  name: z.string().min(2, 'Product name must be at least 2 characters'),
  description: z.string().optional().or(z.literal('')),
  sku: z.string().optional().or(z.literal('')),
  price: z.coerce.number().min(0, 'Price cannot be negative'),
  currency: z.string().min(1, 'Please select a currency'),
  stock_quantity: z.coerce.number().int().min(0, 'Stock cannot be negative'),
  low_stock_threshold: z.coerce.number().int().min(0).optional().nullable(),
  category: z.string().optional().or(z.literal('')),
  image_url: z.string().url('Must be a valid URL').optional().or(z.literal('')),
  is_active: z.boolean(),
})

type ProductFormData = z.infer<typeof productFormSchema>

export const ProductFormPage: React.FC = () => {
  const { productId } = useParams<{ productId: string }>()
  const isEditMode = Boolean(productId && productId !== 'new')
  const navigate = useNavigate()
  const { toast } = useToast()
  const { activeBusiness } = useBusiness()

  const { data: existingProduct, isLoading: isLoadingProduct } = useProduct(productId)
  const createProductMutation = useCreateProduct()
  const updateProductMutation = useUpdateProduct()

  const [formError, setFormError] = useState<string | null>(null)

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<ProductFormData>({
    resolver: zodResolver(productFormSchema),
    defaultValues: {
      name: '',
      description: '',
      sku: '',
      price: 0,
      currency: activeBusiness?.currency || 'USD',
      stock_quantity: 0,
      low_stock_threshold: 5,
      category: '',
      image_url: '',
      is_active: true,
    },
  })

  useEffect(() => {
    if (isEditMode && existingProduct) {
      reset({
        name: existingProduct.name,
        description: existingProduct.description || '',
        sku: existingProduct.sku || '',
        price: existingProduct.price,
        currency: existingProduct.currency || activeBusiness?.currency || 'USD',
        stock_quantity: existingProduct.stock_quantity,
        low_stock_threshold: existingProduct.low_stock_threshold ?? 5,
        category: existingProduct.category || '',
        image_url: existingProduct.image_url || '',
        is_active: existingProduct.is_active,
      })
    }
  }, [isEditMode, existingProduct, reset, activeBusiness])

  const onSubmit = async (values: ProductFormData) => {
    setFormError(null)
    try {
      if (isEditMode && productId) {
        await updateProductMutation.mutateAsync({
          productId,
          productData: {
            name: values.name,
            description: values.description || undefined,
            sku: values.sku || undefined,
            price: values.price,
            currency: values.currency,
            stock_quantity: values.stock_quantity,
            low_stock_threshold: values.low_stock_threshold ?? undefined,
            category: values.category || undefined,
            image_url: values.image_url || undefined,
            is_active: values.is_active,
          },
        })
        toast({
          title: 'Product Updated',
          description: `"${values.name}" was updated successfully.`,
          type: 'success',
        })
      } else {
        await createProductMutation.mutateAsync({
          name: values.name,
          description: values.description || undefined,
          sku: values.sku || undefined,
          price: values.price,
          currency: values.currency,
          stock_quantity: values.stock_quantity,
          low_stock_threshold: values.low_stock_threshold ?? undefined,
          category: values.category || undefined,
          image_url: values.image_url || undefined,
          is_active: values.is_active,
        })
        toast({
          title: 'Product Created',
          description: `"${values.name}" was created successfully.`,
          type: 'success',
        })
      }
      navigate('/products')
    } catch (err: any) {
      setFormError(err.message || 'Failed to save product. Please try again.')
    }
  }

  if (isEditMode && isLoadingProduct) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-48" />
        <Card>
          <CardContent className="p-8 space-y-4">
            <Skeleton className="h-10 w-full" />
            <Skeleton className="h-24 w-full" />
            <Skeleton className="h-10 w-1/2" />
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="space-y-6 max-w-4xl">
      <PageHeader
        title={isEditMode ? 'Edit Product' : 'Add New Product'}
        description={
          isEditMode
            ? 'Update product details, pricing, and stock status.'
            : 'Fill in the information to add an item to your store catalog.'
        }
        backUrl="/products"
        backLabel="Back to Products"
      />

      {formError && (
        <div className="flex items-center gap-2.5 rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800">
          <AlertCircle className="h-5 w-5 flex-shrink-0 text-rose-600" />
          <span>{formError}</span>
        </div>
      )}

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
        <Card>
          <CardHeader>
            <CardTitle className="text-base font-semibold">Basic Details</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <Label htmlFor="name" required>
                Product Name
              </Label>
              <div className="mt-1.5">
                <Input
                  id="name"
                  placeholder="e.g. Ethiopian Yirgacheffe Coffee Beans (250g)"
                  error={errors.name?.message}
                  {...register('name')}
                />
              </div>
            </div>

            <div>
              <Label htmlFor="description">Description</Label>
              <div className="mt-1.5">
                <textarea
                  id="description"
                  rows={3}
                  className="w-full rounded-lg border border-slate-300 p-3 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500"
                  placeholder="Detailed notes, size variations, flavor profile, etc."
                  {...register('description')}
                />
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <Label htmlFor="category">Category</Label>
                <div className="mt-1.5">
                  <Input
                    id="category"
                    placeholder="e.g. Beverages, Apparel, Electronics"
                    {...register('category')}
                  />
                </div>
              </div>

              <div>
                <Label htmlFor="sku">SKU / Item Code</Label>
                <div className="mt-1.5">
                  <Input
                    id="sku"
                    placeholder="e.g. BEAN-ETH-001"
                    {...register('sku')}
                  />
                </div>
              </div>
            </div>

            <div>
              <Label htmlFor="image_url">Image URL</Label>
              <div className="mt-1.5">
                <Input
                  id="image_url"
                  placeholder="https://images.unsplash.com/..."
                  error={errors.image_url?.message}
                  {...register('image_url')}
                />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base font-semibold">Pricing & Inventory</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <Label htmlFor="price" required>
                  Unit Price
                </Label>
                <div className="mt-1.5">
                  <Input
                    id="price"
                    type="number"
                    step="0.01"
                    min="0"
                    placeholder="0.00"
                    error={errors.price?.message}
                    {...register('price')}
                  />
                </div>
              </div>

              <div>
                <Label htmlFor="currency" required>
                  Currency
                </Label>
                <div className="mt-1.5">
                  <Select id="currency" error={errors.currency?.message} {...register('currency')}>
                    {CURRENCIES.map((c) => (
                      <option key={c.code} value={c.code}>
                        {c.label}
                      </option>
                    ))}
                  </Select>
                </div>
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <Label htmlFor="stock_quantity" required>
                  Available Stock Quantity
                </Label>
                <div className="mt-1.5">
                  <Input
                    id="stock_quantity"
                    type="number"
                    min="0"
                    placeholder="0"
                    error={errors.stock_quantity?.message}
                    {...register('stock_quantity')}
                  />
                </div>
              </div>

              <div>
                <Label htmlFor="low_stock_threshold">Low Stock Alert Threshold</Label>
                <div className="mt-1.5">
                  <Input
                    id="low_stock_threshold"
                    type="number"
                    min="0"
                    placeholder="5"
                    helperText="Alerts when inventory falls at or below this level"
                    {...register('low_stock_threshold')}
                  />
                </div>
              </div>
            </div>

            <div className="pt-2">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  className="h-4 w-4 rounded border-slate-300 text-primary-600 focus:ring-primary-500"
                  {...register('is_active')}
                />
                <span className="text-sm font-medium text-slate-700">
                  Active (available for ordering)
                </span>
              </label>
            </div>
          </CardContent>
        </Card>

        <div className="flex items-center justify-end gap-3 pt-2">
          <Button
            type="button"
            variant="outline"
            onClick={() => navigate('/products')}
            disabled={isSubmitting}
          >
            Cancel
          </Button>
          <Button type="submit" size="md" isLoading={isSubmitting}>
            {isEditMode ? 'Update Product' : 'Create Product'}
          </Button>
        </div>
      </form>
    </div>
  )
}
export default ProductFormPage
