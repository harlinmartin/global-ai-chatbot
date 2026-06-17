'use client';

import { useActionState } from 'react';
import { login } from '@/lib/auth';
import Link from 'next/link';

export default function LoginPage() {
  const [state, formAction, isPending] = useActionState(login, null);

  return (
    <div className="min-h-screen bg-neutral-950 flex flex-col items-center justify-center p-4">
      <div className="w-full max-w-md bg-neutral-900 border border-neutral-800 rounded-2xl p-8 shadow-xl">
        <div className="mb-8 text-center">
          <h1 className="text-2xl font-semibold text-neutral-100">Welcome Back</h1>
          <p className="text-neutral-400 mt-2">Sign in to your AI workspace</p>
        </div>

        <form action={formAction} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-neutral-300 mb-1">Email</label>
            <input 
              name="email" 
              type="email" 
              required 
              className="w-full bg-neutral-950 border border-neutral-800 rounded-lg px-4 py-3 text-neutral-100 focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500 transition-colors"
              placeholder="you@example.com"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-neutral-300 mb-1">Password</label>
            <input 
              name="password" 
              type="password" 
              required 
              className="w-full bg-neutral-950 border border-neutral-800 rounded-lg px-4 py-3 text-neutral-100 focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500 transition-colors"
              placeholder="••••••••"
            />
          </div>

          {state?.error && (
            <div className="p-3 bg-red-500/10 border border-red-500/20 rounded-lg text-red-400 text-sm">
              {state.error}
            </div>
          )}

          <button 
            type="submit" 
            disabled={isPending}
            className="w-full bg-blue-600 hover:bg-blue-500 text-white font-medium py-3 rounded-lg transition-colors disabled:opacity-50 mt-4"
          >
            {isPending ? 'Signing in...' : 'Sign In'}
          </button>
        </form>

        <div className="mt-6 text-center text-sm text-neutral-400">
          Don't have an account? <Link href="/register" className="text-blue-400 hover:text-blue-300">Sign up</Link>
        </div>
      </div>
    </div>
  );
}
