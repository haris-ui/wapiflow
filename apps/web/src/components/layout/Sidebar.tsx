import React from 'react'
import { NavLink, useNavigate } from 'react-router-dom'
import {
  LayoutDashboard,
  ShoppingCart,
  MessageCircle,
  Users,
  Package,
  BarChart2,
  TrendingUp,
  Settings,
  LogOut,
  X,
} from 'lucide-react'
import { useAuth } from '@/hooks/useAuth'
import { cn } from '@/lib/utils'

interface SidebarProps {
  onCloseMobile?: () => void
}

interface NavItem {
  label: string
  href: string
  icon: React.ComponentType<{ className?: string }>
  badge?: string
  disabled?: boolean
}

const NAV_ITEMS: NavItem[] = [
  { label: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
  { label: 'Orders', href: '/orders', icon: ShoppingCart },
  {
    label: 'WhatsApp',
    href: '#whatsapp',
    icon: MessageCircle,
    badge: 'Coming Soon',
    disabled: true,
  },
  { label: 'Customers', href: '/customers', icon: Users },
  { label: 'Products', href: '/products', icon: Package },
  {
    label: 'Inventory',
    href: '#inventory',
    icon: BarChart2,
    badge: 'Coming Soon',
    disabled: true,
  },
  {
    label: 'Reports',
    href: '#reports',
    icon: TrendingUp,
    badge: 'Coming Soon',
    disabled: true,
  },
  { label: 'Settings', href: '#settings', icon: Settings, badge: 'Coming Soon', disabled: true },
]

export const Sidebar: React.FC<SidebarProps> = ({ onCloseMobile }) => {
  const { user, signOut } = useAuth()
  const navigate = useNavigate()

  const handleSignOut = async () => {
    try {
      await signOut()
      navigate('/login')
    } catch (err) {
      console.error('Error signing out', err)
    }
  }

  const userInitial = user?.email ? user.email.charAt(0).toUpperCase() : 'U'
  const userName = user?.user_metadata?.full_name || user?.email?.split('@')[0] || 'User'

  return (
    <aside className="flex h-full w-64 flex-col border-r border-slate-200 bg-white">
      {/* Brand Header */}
      <div className="flex h-16 items-center justify-between px-6 border-b border-slate-100">
        <NavLink to="/dashboard" className="flex items-center gap-2.5">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-primary-600 text-white shadow-sm shadow-primary-500/30">
            <MessageCircle className="h-5 w-5" />
          </div>
          <div>
            <span className="font-bold text-lg text-slate-900 tracking-tight">Wapi</span>
            <span className="font-bold text-lg text-primary-600 tracking-tight">Flow</span>
          </div>
        </NavLink>
        {onCloseMobile && (
          <button
            onClick={onCloseMobile}
            className="md:hidden p-1.5 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-100"
          >
            <X className="h-5 w-5" />
          </button>
        )}
      </div>

      {/* Navigation */}
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-1">
        <p className="px-3 text-[11px] font-semibold uppercase tracking-wider text-slate-400 mb-2">
          Operations
        </p>
        {NAV_ITEMS.map((item) => {
          const Icon = item.icon

          if (item.disabled) {
            return (
              <div
                key={item.label}
                className="flex items-center justify-between px-3 py-2.5 text-sm font-medium text-slate-400 rounded-lg cursor-not-allowed select-none opacity-60"
              >
                <div className="flex items-center gap-3">
                  <Icon className="h-4 w-4" />
                  <span>{item.label}</span>
                </div>
                {item.badge && (
                  <span className="rounded bg-slate-100 px-1.5 py-0.5 text-[10px] font-medium text-slate-500">
                    {item.badge}
                  </span>
                )}
              </div>
            )
          }

          return (
            <NavLink
              key={item.label}
              to={item.href}
              onClick={onCloseMobile}
              className={({ isActive }) =>
                cn(
                  'flex items-center justify-between px-3 py-2.5 text-sm font-medium rounded-lg transition-colors',
                  isActive
                    ? 'bg-primary-50 text-primary-700 font-semibold shadow-xs'
                    : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'
                )
              }
            >
              <div className="flex items-center gap-3">
                <Icon className="h-4 w-4" />
                <span>{item.label}</span>
              </div>
            </NavLink>
          )
        })}
      </div>

      {/* User profile footer */}
      <div className="border-t border-slate-100 p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3 min-w-0">
            <div className="flex h-9 w-9 items-center justify-center rounded-full bg-slate-100 font-bold text-slate-700 text-sm flex-shrink-0 border border-slate-200">
              {userInitial}
            </div>
            <div className="truncate">
              <p className="text-sm font-medium text-slate-900 truncate">{userName}</p>
              <p className="text-xs text-slate-500 truncate">{user?.email}</p>
            </div>
          </div>
          <button
            onClick={handleSignOut}
            title="Sign out"
            className="p-1.5 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded-lg transition-colors"
          >
            <LogOut className="h-4 w-4" />
          </button>
        </div>
      </div>
    </aside>
  )
}
