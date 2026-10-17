import React from 'react'
import {
  createBrowserRouter,
  Navigate,
  useLocation,
} from 'react-router-dom'
import { useAuth } from '@/hooks/useAuth'
import { useBusiness } from '@/hooks/useBusiness'
import { Spinner } from '@/components/ui/Spinner'

// Layouts
import { AppLayout } from '@/components/layout/AppLayout'
import { AuthLayout } from '@/components/layout/AuthLayout'

// Pages
import LoginPage from '@/pages/auth/LoginPage'
import RegisterPage from '@/pages/auth/RegisterPage'
import ForgotPasswordPage from '@/pages/auth/ForgotPasswordPage'
import CreateBusinessPage from '@/pages/onboarding/CreateBusinessPage'
import DashboardPage from '@/pages/dashboard/DashboardPage'
import OrdersPage from '@/pages/orders/OrdersPage'
import OrderDetailPage from '@/pages/orders/OrderDetailPage'
import CreateOrderPage from '@/pages/orders/CreateOrderPage'
import ProductsPage from '@/pages/products/ProductsPage'
import ProductFormPage from '@/pages/products/ProductFormPage'
import CustomersPage from '@/pages/customers/CustomersPage'
import CustomerDetailPage from '@/pages/customers/CustomerDetailPage'
import NotFoundPage from '@/pages/NotFoundPage'

/**
 * Route wrapper requiring valid Supabase authentication.
 * If authenticated with 0 businesses, directs to business setup.
 */
export const ProtectedRoute: React.FC<{ children: React.ReactElement }> = ({ children }) => {
  const { isAuthenticated, isLoading: isAuthLoading } = useAuth()
  const { businesses, isLoading: isBizLoading } = useBusiness()
  const location = useLocation()

  if (isAuthLoading) {
    return (
      <div className="flex h-screen w-full items-center justify-center bg-slate-50">
        <Spinner size="lg" className="text-primary-600" />
      </div>
    )
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />
  }

  // If user is logged in, finished loading businesses, and has no businesses:
  // Redirect to business creation onboarding unless already on that page.
  if (
    !isBizLoading &&
    businesses.length === 0 &&
    location.pathname !== '/onboarding/create-business'
  ) {
    return <Navigate to="/onboarding/create-business" replace />
  }

  return children
}

/**
 * Route wrapper that redirects authenticated users to the dashboard
 */
export const AfterAuthRoute: React.FC<{ children: React.ReactElement }> = ({ children }) => {
  const { isAuthenticated, isLoading } = useAuth()

  if (isLoading) {
    return (
      <div className="flex h-screen w-full items-center justify-center bg-slate-50">
        <Spinner size="lg" className="text-primary-600" />
      </div>
    )
  }

  if (isAuthenticated) {
    return <Navigate to="/dashboard" replace />
  }

  return children
}

export const router = createBrowserRouter([
  // Root Redirect
  {
    path: '/',
    element: <Navigate to="/dashboard" replace />,
  },

  // Auth Routes (Login, Register, Forgot Password)
  {
    element: (
      <AfterAuthRoute>
        <AuthLayout />
      </AfterAuthRoute>
    ),
    children: [
      {
        path: '/login',
        element: <LoginPage />,
      },
      {
        path: '/register',
        element: <RegisterPage />,
      },
      {
        path: '/forgot-password',
        element: <ForgotPasswordPage />,
      },
    ],
  },

  // Onboarding (Protected, standalone view)
  {
    path: '/onboarding/create-business',
    element: (
      <ProtectedRoute>
        <CreateBusinessPage />
      </ProtectedRoute>
    ),
  },

  // Authenticated App Routes (AppLayout with sidebar + header)
  {
    element: (
      <ProtectedRoute>
        <AppLayout />
      </ProtectedRoute>
    ),
    children: [
      {
        path: '/dashboard',
        element: <DashboardPage />,
      },
      {
        path: '/orders',
        element: <OrdersPage />,
      },
      {
        path: '/orders/new',
        element: <CreateOrderPage />,
      },
      {
        path: '/orders/:orderId',
        element: <OrderDetailPage />,
      },
      {
        path: '/products',
        element: <ProductsPage />,
      },
      {
        path: '/products/new',
        element: <ProductFormPage />,
      },
      {
        path: '/products/:productId/edit',
        element: <ProductFormPage />,
      },
      {
        path: '/customers',
        element: <CustomersPage />,
      },
      {
        path: '/customers/:customerId',
        element: <CustomerDetailPage />,
      },
    ],
  },

  // 404 Catch-All
  {
    path: '*',
    element: <NotFoundPage />,
  },
])
