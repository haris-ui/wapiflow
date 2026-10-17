import React from 'react'
import { Outlet, Link } from 'react-router-dom'
import { MessageCircle } from 'lucide-react'

export const AuthLayout: React.FC = () => {
  return (
    <div className="min-h-screen bg-slate-50 flex flex-col justify-center py-12 sm:px-6 lg:px-8">
      <div className="sm:mx-auto sm:w-full sm:max-w-md text-center">
        <Link to="/" className="inline-flex items-center gap-2.5 mb-3">
          <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-primary-600 text-white shadow-md shadow-primary-500/30">
            <MessageCircle className="h-6 w-6" />
          </div>
          <span className="font-bold text-2xl text-slate-900 tracking-tight">
            Wapi<span className="text-primary-600">Flow</span>
          </span>
        </Link>
        <p className="text-sm text-slate-500 font-medium">
          Turn WhatsApp conversations into business operations
        </p>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md px-4 sm:px-0">
        <div className="bg-white py-8 px-6 shadow-sm border border-slate-200 rounded-2xl sm:px-10">
          <Outlet />
        </div>
        <div className="mt-6 text-center text-xs text-slate-400">
          &copy; {new Date().getFullYear()} WapiFlow Inc. All rights reserved.
        </div>
      </div>
    </div>
  )
}
