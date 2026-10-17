import React from 'react'
import * as DropdownMenu from '@radix-ui/react-dropdown-menu'
import { Menu, LogOut, UserCircle, Plus } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { BusinessSelector } from '@/components/shared/BusinessSelector'
import { useAuth } from '@/hooks/useAuth'

interface HeaderProps {
  onOpenMobileSidebar: () => void
}

export const Header: React.FC<HeaderProps> = ({ onOpenMobileSidebar }) => {
  const { user, signOut } = useAuth()
  const navigate = useNavigate()

  const handleSignOut = async () => {
    try {
      await signOut()
      navigate('/login')
    } catch (err) {
      console.error('Logout error:', err)
    }
  }

  const userInitial = user?.email ? user.email.charAt(0).toUpperCase() : 'U'
  const userName = user?.user_metadata?.full_name || user?.email?.split('@')[0] || 'User'

  return (
    <header className="sticky top-0 z-30 flex h-16 w-full items-center justify-between border-b border-slate-200 bg-white/95 px-4 md:px-8 backdrop-blur-sm">
      <div className="flex items-center gap-3">
        <button
          onClick={onOpenMobileSidebar}
          className="md:hidden p-2 rounded-lg text-slate-600 hover:bg-slate-100 focus:outline-none"
          aria-label="Toggle navigation menu"
        >
          <Menu className="h-5 w-5" />
        </button>

        {/* Business Selector Dropdown */}
        <BusinessSelector />
      </div>

      <div className="flex items-center gap-4">
        {/* User avatar dropdown */}
        <DropdownMenu.Root>
          <DropdownMenu.Trigger asChild>
            <button
              className="flex items-center gap-2 rounded-full focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2"
              aria-label="User account menu"
            >
              <div className="flex h-9 w-9 items-center justify-center rounded-full bg-primary-100 font-bold text-primary-700 text-sm border border-primary-200">
                {userInitial}
              </div>
            </button>
          </DropdownMenu.Trigger>

          <DropdownMenu.Portal>
            <DropdownMenu.Content
              className="z-50 min-w-[200px] overflow-hidden rounded-xl border border-slate-200 bg-white p-1.5 text-slate-800 shadow-lg animate-in fade-in-80 zoom-in-95"
              align="end"
              sideOffset={5}
            >
              <div className="px-3 py-2 border-b border-slate-100">
                <p className="text-sm font-semibold text-slate-900 leading-tight">{userName}</p>
                <p className="text-xs text-slate-500 truncate mt-0.5">{user?.email}</p>
              </div>

              <DropdownMenu.Item
                onSelect={() => navigate('/onboarding/create-business')}
                className="flex items-center gap-2.5 px-3 py-2 text-sm text-slate-700 rounded-lg cursor-pointer hover:bg-slate-100 outline-none transition-colors"
              >
                <Plus className="h-4 w-4 text-slate-500" />
                <span>New Business</span>
              </DropdownMenu.Item>

              <DropdownMenu.Item
                onSelect={() => {}}
                className="flex items-center gap-2.5 px-3 py-2 text-sm text-slate-400 rounded-lg cursor-not-allowed select-none opacity-60"
              >
                <UserCircle className="h-4 w-4" />
                <span>Profile Settings</span>
              </DropdownMenu.Item>

              <DropdownMenu.Separator className="h-px bg-slate-100 my-1" />

              <DropdownMenu.Item
                onSelect={handleSignOut}
                className="flex items-center gap-2.5 px-3 py-2 text-sm text-rose-600 font-medium rounded-lg cursor-pointer hover:bg-rose-50 outline-none transition-colors"
              >
                <LogOut className="h-4 w-4 text-rose-600" />
                <span>Sign Out</span>
              </DropdownMenu.Item>
            </DropdownMenu.Content>
          </DropdownMenu.Portal>
        </DropdownMenu.Root>
      </div>
    </header>
  )
}
