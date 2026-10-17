import React, { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Plus, Search, Edit2, Trash2, Package, RefreshCw } from 'lucide-react'
import { useProducts, useDeleteProduct } from '@/hooks/useProducts'
import { useBusiness } from '@/hooks/useBusiness'
import { PageHeader } from '@/components/shared/PageHeader'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Select } from '@/components/ui/Select'
import { Badge } from '@/components/ui/Badge'
import { Pagination } from '@/components/ui/Pagination'
import { EmptyState } from '@/components/ui/EmptyState'
import { ConfirmDialog } from '@/components/shared/ConfirmDialog'
import { TableRowSkeleton } from '@/components/ui/Skeleton'
import { formatCurrency } from '@/lib/utils'
import { Product } from '@/types'
import { useToast } from '@/components/ui/Toast'

export const ProductsPage: React.FC = () => {
  const navigate = useNavigate()
  const { toast } = useToast()
  const { activeBusiness } = useBusiness()

  const [page, setPage] = useState<number>(1)
  const [pageSize] = useState<number>(10)
  const [search, setSearch] = useState<string>('')
  const [statusFilter, setStatusFilter] = useState<'all' | 'active' | 'archived'>('all')

  const [productToDelete, setProductToDelete] = useState<Product | null>(null)

  const {
    data,
    isLoading,
    isError,
    error,
    refetch,
  } = useProducts({
    page,
    pageSize,
    search,
    is_active: statusFilter === 'all' ? null : statusFilter === 'active',
  })

  const deleteProductMutation = useDeleteProduct()

  const products = data?.items || []
  const total = data?.total || 0
  const totalPages = data?.total_pages || Math.ceil(total / pageSize) || 1
  const currency = activeBusiness?.currency || 'USD'

  const handleDeleteConfirm = async () => {
    if (!productToDelete) return
    try {
      await deleteProductMutation.mutateAsync(productToDelete.id)
      toast({
        title: 'Product Deleted',
        description: `"${productToDelete.name}" was successfully removed.`,
        type: 'success',
      })
      setProductToDelete(null)
    } catch (err: any) {
      toast({
        title: 'Error deleting product',
        description: err.message || 'Failed to delete product.',
        type: 'error',
      })
    }
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Products"
        description="Manage your inventory catalog, stock levels, and pricing."
        actions={
          <Link to="/products/new">
            <Button variant="primary" size="md" leftIcon={<Plus className="h-4 w-4" />}>
              Add Product
            </Button>
          </Link>
        }
      />

      {/* Search and Filters */}
      <div className="flex flex-col sm:flex-row items-center gap-4 bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
        <div className="w-full sm:flex-1">
          <Input
            placeholder="Search products by name or SKU..."
            leftIcon={<Search className="h-4 w-4" />}
            value={search}
            onChange={(e) => {
              setSearch(e.target.value)
              setPage(1)
            }}
          />
        </div>
        <div className="w-full sm:w-48">
          <Select
            value={statusFilter}
            onChange={(e) => {
              setStatusFilter(e.target.value as 'all' | 'active' | 'archived')
              setPage(1)
            }}
          >
            <option value="all">All Products</option>
            <option value="active">Active only</option>
            <option value="archived">Archived / Inactive</option>
          </Select>
        </div>
      </div>

      {isError && (
        <div className="rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800 flex items-center justify-between">
          <span>Failed to load products: {(error as any)?.message || 'Network error'}</span>
          <Button variant="outline" size="sm" onClick={() => refetch()} leftIcon={<RefreshCw className="h-3.5 w-3.5" />}>
            Retry
          </Button>
        </div>
      )}

      {/* Products Table */}
      <div className="rounded-xl border border-slate-200 bg-white overflow-hidden shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-50/75 border-b border-slate-200 text-xs font-semibold uppercase tracking-wider text-slate-500">
              <tr>
                <th className="px-6 py-3.5">Product</th>
                <th className="px-6 py-3.5">SKU</th>
                <th className="px-6 py-3.5">Price</th>
                <th className="px-6 py-3.5">Stock</th>
                <th className="px-6 py-3.5">Status</th>
                <th className="px-6 py-3.5 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {isLoading ? (
                Array.from({ length: 6 }).map((_, idx) => (
                  <TableRowSkeleton key={idx} columns={6} />
                ))
              ) : products.length === 0 ? (
                <tr>
                  <td colSpan={6} className="py-12">
                    <EmptyState
                      title="No products found"
                      description={
                        search
                          ? `No products matching "${search}".`
                          : 'You haven’t added any products to your catalog yet.'
                      }
                      actionLabel={!search ? 'Add First Product' : undefined}
                      onAction={() => navigate('/products/new')}
                    />
                  </td>
                </tr>
              ) : (
                products.map((product) => {
                  const isLowStock =
                    product.low_stock_threshold !== null &&
                    product.low_stock_threshold !== undefined &&
                    product.stock_quantity <= product.low_stock_threshold

                  return (
                    <tr
                      key={product.id}
                      className="hover:bg-slate-50/80 transition-colors"
                    >
                      <td className="px-6 py-4">
                        <div className="flex items-center gap-3">
                          <div className="h-10 w-10 rounded-lg bg-slate-100 flex items-center justify-center flex-shrink-0 border border-slate-200 overflow-hidden">
                            {product.image_url ? (
                              <img
                                src={product.image_url}
                                alt={product.name}
                                className="h-full w-full object-cover"
                              />
                            ) : (
                              <Package className="h-5 w-5 text-slate-400" />
                            )}
                          </div>
                          <div>
                            <div className="font-medium text-slate-900">{product.name}</div>
                            {product.category && (
                              <div className="text-xs text-slate-400">{product.category}</div>
                            )}
                          </div>
                        </div>
                      </td>
                      <td className="px-6 py-4 font-mono text-xs text-slate-600">
                        {product.sku || '—'}
                      </td>
                      <td className="px-6 py-4 font-semibold text-slate-900">
                        {formatCurrency(product.price, product.currency || currency)}
                      </td>
                      <td className="px-6 py-4">
                        <div className="flex items-center gap-2">
                          <span
                            className={`font-medium ${
                              isLowStock ? 'text-amber-600' : 'text-slate-700'
                            }`}
                          >
                            {product.stock_quantity}
                          </span>
                          {isLowStock && (
                            <span className="rounded bg-amber-50 px-1.5 py-0.5 text-[10px] font-semibold text-amber-700 border border-amber-200">
                              Low Stock
                            </span>
                          )}
                        </div>
                      </td>
                      <td className="px-6 py-4">
                        <Badge variant={product.is_active ? 'delivered' : 'secondary'}>
                          {product.is_active ? 'Active' : 'Archived'}
                        </Badge>
                      </td>
                      <td className="px-6 py-4 text-right">
                        <div className="flex items-center justify-end gap-1">
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => navigate(`/products/${product.id}/edit`)}
                            title="Edit Product"
                          >
                            <Edit2 className="h-4 w-4 text-slate-500" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => setProductToDelete(product)}
                            title="Delete Product"
                            className="hover:text-rose-600 hover:bg-rose-50"
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </div>
                      </td>
                    </tr>
                  )
                })
              )}
            </tbody>
          </table>
        </div>

        {total > 0 && (
          <div className="border-t border-slate-100 bg-white">
            <Pagination
              currentPage={page}
              totalPages={totalPages}
              totalItems={total}
              pageSize={pageSize}
              onPageChange={(p) => setPage(p)}
            />
          </div>
        )}
      </div>

      {/* Delete Confirmation Dialog */}
      <ConfirmDialog
        isOpen={!!productToDelete}
        onClose={() => setProductToDelete(null)}
        onConfirm={handleDeleteConfirm}
        isLoading={deleteProductMutation.isPending}
        variant="destructive"
        title="Delete Product"
        description={`Are you sure you want to permanently remove "${productToDelete?.name}"? This action cannot be undone.`}
        confirmText="Delete Product"
      />
    </div>
  )
}
export default ProductsPage
