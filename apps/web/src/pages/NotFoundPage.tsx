import React from 'react'
import { Link } from 'react-router-dom'
import { Home, HelpCircle } from 'lucide-react'
import { Button } from '@/components/ui/Button'

export const NotFoundPage: React.FC = () => {
  return (
    <div className="min-h-screen bg-slate-50 flex flex-col justify-center items-center px-4 text-center">
      <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-primary-100 text-primary-600 mb-6 shadow-sm">
        <HelpCircle className="h-8 w-8" />
      </div>
      <h1 className="text-6xl font-extrabold text-slate-900 tracking-tight">404</h1>
      <h2 className="mt-3 text-2xl font-bold text-slate-800">Page not found</h2>
      <p className="mt-2 text-sm text-slate-500 max-w-sm">
        Sorry, we couldn’t find the page you’re looking for. It might have been moved or removed.
      </p>
      <div className="mt-8 flex gap-3">
        <Link to="/dashboard">
          <Button variant="primary" size="md" leftIcon={<Home className="h-4 w-4" />}>
            Back to Dashboard
          </Button>
        </Link>
      </div>
    </div>
  )
}
export default NotFoundPage
