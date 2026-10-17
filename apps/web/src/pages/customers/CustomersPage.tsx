import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Search, Eye, RefreshCw, UserPlus } from 'lucide-react'
import { useCustomers, useCreateCustomer } from '@/hooks/useCustomers'
import { PageHeader } from '@/components/shared/PageHeader'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Pagination } from '@/components/ui/Pagination'
import { EmptyState } from '@/components/ui/EmptyState'
import { TableRowSkeleton } from '@/components/ui/Skeleton'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/Dialog'
import { Label } from '@/components/ui/Label'
import { useToast } from '@/components/ui/Toast'

export const CustomersPage: React.FC = () => {
  const navigate = useNavigate()
  const { toast } = useToast()

  const [page, setPage] = useState<number>(1)
  const [pageSize] = useState<number>(10)
  const [search, setSearch] = useState<string>('')

  // Add Customer modal
  const [isAddOpen, setIsAddOpen] = useState(false)
  const [newName, setNewName] = useState('')
  const [newPhone, setNewPhone] = useState('')
  const [newEmail, setNewEmail] = useState('')
  const [newAddress, setNewAddress] = useState('')
  const [newCity, setNewCity] = useState('')

  const { data, isLoading, isError, error, refetch } = useCustomers({
    page,
    pageSize,
    search,
  })

  const createCustomerMutation = useCreateCustomer()

  const customers = data?.items || []
  const total = data?.total || 0
  const totalPages = data?.total_pages || Math.ceil(total / pageSize) || 1

  const handleCreateCustomer = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!newName || !newPhone) return

    try {
      await createCustomerMutation.mutateAsync({
        name: newName,
        phone_number: newPhone,
        email: newEmail || undefined,
        address: newAddress || undefined,
        city: newCity || undefined,
      })
      toast({
        title: 'Customer Added',
        description: `Customer "${newName}" has been saved.`,
        type: 'success',
      })
      setIsAddOpen(false)
      setNewName('')
      setNewPhone('')
      setNewEmail('')
      setNewAddress('')
      setNewCity('')
    } catch (err: any) {
      toast({
        title: 'Failed to add customer',
        description: err.message || 'Please check the details and try again.',
        type: 'error',
      })
    }
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Customers"
        description="View contact information and past order histories of your WhatsApp buyers."
        actions={
          <Button
            variant="primary"
            size="md"
            leftIcon={<UserPlus className="h-4 w-4" />}
            onClick={() => setIsAddOpen(true)}
          >
            Add Customer
          </Button>
        }
      />

      {/* Search Input */}
      <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm max-w-md">
        <Input
          placeholder="Search by customer name or phone..."
          leftIcon={<Search className="h-4 w-4" />}
          value={search}
          onChange={(e) => {
            setSearch(e.target.value)
            setPage(1)
          }}
        />
      </div>

      {isError && (
        <div className="rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800 flex items-center justify-between">
          <span>Failed to load customers: {(error as any)?.message || 'Network error'}</span>
          <Button variant="outline" size="sm" onClick={() => refetch()} leftIcon={<RefreshCw className="h-3.5 w-3.5" />}>
            Retry
          </Button>
        </div>
      )}

      {/* Customers Table */}
      <div className="rounded-xl border border-slate-200 bg-white overflow-hidden shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-50/75 border-b border-slate-200 text-xs font-semibold uppercase tracking-wider text-slate-500">
              <tr>
                <th className="px-6 py-3.5">Customer Name</th>
                <th className="px-6 py-3.5">Phone Number</th>
                <th className="px-6 py-3.5">Email</th>
                <th className="px-6 py-3.5">City</th>
                <th className="px-6 py-3.5">Total Orders</th>
                <th className="px-6 py-3.5 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {isLoading ? (
                Array.from({ length: 6 }).map((_, idx) => (
                  <TableRowSkeleton key={idx} columns={6} />
                ))
              ) : customers.length === 0 ? (
                <tr>
                  <td colSpan={6} className="py-12">
                    <EmptyState
                      title="No customers found"
                      description={
                        search
                          ? `No customers found for "${search}".`
                          : 'Your customer list will populate as buyers message your store or place orders.'
                      }
                      actionLabel={!search ? 'Add Customer' : undefined}
                      onAction={() => setIsAddOpen(true)}
                    />
                  </td>
                </tr>
              ) : (
                customers.map((customer) => (
                  <tr
                    key={customer.id}
                    onClick={() => navigate(`/customers/${customer.id}`)}
                    className="cursor-pointer hover:bg-slate-50/80 transition-colors"
                  >
                    <td className="px-6 py-4 font-medium text-slate-900">
                      {customer.name}
                    </td>
                    <td className="px-6 py-4 text-slate-600 font-mono text-xs">
                      {customer.phone_number}
                    </td>
                    <td className="px-6 py-4 text-slate-500">
                      {customer.email || '—'}
                    </td>
                    <td className="px-6 py-4 text-slate-500">
                      {customer.city || '—'}
                    </td>
                    <td className="px-6 py-4">
                      <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-slate-100 text-slate-700">
                        {customer.total_orders || 0} orders
                      </span>
                    </td>
                    <td className="px-6 py-4 text-right">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={(e) => {
                          e.stopPropagation()
                          navigate(`/customers/${customer.id}`)
                        }}
                      >
                        <Eye className="h-4 w-4 mr-1 text-slate-400" />
                        View
                      </Button>
                    </td>
                  </tr>
                ))
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

      {/* Add Customer Dialog */}
      <Dialog open={isAddOpen} onOpenChange={setIsAddOpen}>
        <DialogContent>
          <form onSubmit={handleCreateCustomer}>
            <DialogHeader>
              <DialogTitle>Add Customer</DialogTitle>
            </DialogHeader>
            <div className="space-y-4 py-4">
              <div>
                <Label htmlFor="cust-name" required>
                  Customer Name
                </Label>
                <div className="mt-1">
                  <Input
                    id="cust-name"
                    required
                    value={newName}
                    onChange={(e) => setNewName(e.target.value)}
                    placeholder="e.g. John Doe"
                  />
                </div>
              </div>

              <div>
                <Label htmlFor="cust-phone" required>
                  WhatsApp Phone Number
                </Label>
                <div className="mt-1">
                  <Input
                    id="cust-phone"
                    required
                    value={newPhone}
                    onChange={(e) => setNewPhone(e.target.value)}
                    placeholder="+1234567890"
                  />
                </div>
              </div>

              <div>
                <Label htmlFor="cust-email">Email Address</Label>
                <div className="mt-1">
                  <Input
                    id="cust-email"
                    type="email"
                    value={newEmail}
                    onChange={(e) => setNewEmail(e.target.value)}
                    placeholder="john@example.com"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <Label htmlFor="cust-address">Street Address</Label>
                  <div className="mt-1">
                    <Input
                      id="cust-address"
                      value={newAddress}
                      onChange={(e) => setNewAddress(e.target.value)}
                      placeholder="123 Main St"
                    />
                  </div>
                </div>
                <div>
                  <Label htmlFor="cust-city">City</Label>
                  <div className="mt-1">
                    <Input
                      id="cust-city"
                      value={newCity}
                      onChange={(e) => setNewCity(e.target.value)}
                      placeholder="New York"
                    />
                  </div>
                </div>
              </div>
            </div>

            <DialogFooter>
              <Button
                type="button"
                variant="outline"
                onClick={() => setIsAddOpen(false)}
                disabled={createCustomerMutation.isPending}
              >
                Cancel
              </Button>
              <Button
                type="submit"
                variant="primary"
                isLoading={createCustomerMutation.isPending}
              >
                Save Customer
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  )
}
export default CustomersPage
