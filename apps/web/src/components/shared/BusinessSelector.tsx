import React from 'react'
import * as DropdownMenu from '@radix-ui/react-dropdown-menu'
import { Building2, Check, ChevronsUpDown, Plus } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { useBusiness } from '@/hooks/useBusiness'
import { cn } from '@/lib/utils'

export const BusinessSelector: React.FC = () => {
  const { businesses, activeBusiness, setActiveBusiness } = useBusiness()
  const navigate = useNavigate()

  return (
    <DropdownMenu.Root>
      <DropdownMenu.Trigger asChild>
        <button
          className={cn(
            'flex items-center justify-between w-56 px-3 py-2 text-sm font-medium text-slate-800 bg-white border border-slate-200 rounded-lg shadow-sm hover:bg-slate-50 focus:outline-none focus:ring-2 focus:ring-primary-500 transition-colors'
          )}
          aria-label="Select business"
        >
          <div className="flex items-center gap-2 truncate">
            <div className="flex h-6 w-6 items-center justify-center rounded bg-primary-100 text-primary-700 flex-shrink-0">
              <Building2 className="h-3.5 w-3.5" />
            </div>
            <span className="truncate font-semibold">
              {activeBusiness ? activeBusiness.name : 'Select Business'}
            </span>
          </div>
          <ChevronsUpDown className="h-4 w-4 text-slate-400 flex-shrink-0 ml-1" />
        </button>
      </DropdownMenu.Trigger>

      <DropdownMenu.Portal>
        <DropdownMenu.Content
          className="z-50 min-w-[224px] overflow-hidden rounded-xl border border-slate-200 bg-white p-1.5 text-slate-800 shadow-lg animate-in fade-in-80 zoom-in-95"
          align="start"
          sideOffset={5}
        >
          <DropdownMenu.Label className="px-2 py-1.5 text-xs font-semibold uppercase tracking-wider text-slate-400">
            Your Businesses
          </DropdownMenu.Label>

          {businesses.map((biz) => {
            const isSelected = activeBusiness?.id === biz.id
            return (
              <DropdownMenu.Item
                key={biz.id}
                onSelect={() => setActiveBusiness(biz)}
                className={cn(
                  'flex items-center justify-between px-2.5 py-2 text-sm rounded-lg cursor-pointer outline-none transition-colors select-none',
                  isSelected
                    ? 'bg-primary-50 text-primary-900 font-medium'
                    : 'hover:bg-slate-100 text-slate-700'
                )}
              >
                <div className="flex items-center gap-2 truncate">
                  <div className="flex h-5 w-5 items-center justify-center rounded bg-slate-100 text-slate-600">
                    <Building2 className="h-3 w-3" />
                  </div>
                  <span className="truncate">{biz.name}</span>
                </div>
                {isSelected && <Check className="h-4 w-4 text-primary-600 ml-2" />}
              </DropdownMenu.Item>
            )
          })}

          <DropdownMenu.Separator className="h-px bg-slate-100 my-1" />

          <DropdownMenu.Item
            onSelect={() => navigate('/onboarding/create-business')}
            className="flex items-center gap-2 px-2.5 py-2 text-sm text-primary-700 font-medium rounded-lg cursor-pointer hover:bg-primary-50 outline-none transition-colors"
          >
            <Plus className="h-4 w-4 text-primary-600" />
            <span>Create New Business</span>
          </DropdownMenu.Item>
        </DropdownMenu.Content>
      </DropdownMenu.Portal>
    </DropdownMenu.Root>
  )
}
