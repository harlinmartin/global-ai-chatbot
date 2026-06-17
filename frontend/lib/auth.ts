'use server'

import { cookies } from 'next/headers';
import { redirect } from 'next/navigation';

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8001';

export async function login(prevState: any, formData: FormData) {
  const email = formData.get('email');
  const password = formData.get('password');

  if (!email || !password) return { error: 'Email and password required' };

  const res = await fetch(`${BACKEND_URL}/api/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams({ username: email as string, password: password as string }),
  });

  if (!res.ok) {
    return { error: 'Invalid credentials' };
  }

  const data = await res.json();
  const cookieStore = await cookies();
  cookieStore.set('token', data.access_token, {
    httpOnly: true,
    secure: process.env.NODE_ENV === 'production',
    sameSite: 'lax',
    path: '/',
  });

  redirect('/chat');
}

export async function register(prevState: any, formData: FormData) {
  const email = formData.get('email');
  const password = formData.get('password');

  if (!email || !password) return { error: 'Email and password required' };

  const res = await fetch(`${BACKEND_URL}/api/auth/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  });

  if (!res.ok) {
    const errorData = await res.json();
    return { error: errorData.detail || 'Registration failed' };
  }

  // Auto-login after registration
  return login(prevState, formData);
}

export async function logout() {
  const cookieStore = await cookies();
  cookieStore.delete('token');
  redirect('/login');
}
