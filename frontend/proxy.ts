import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

export function proxy(request: NextRequest) {
  const token = request.cookies.get('token')?.value;
  const { pathname } = request.nextUrl;

  const isAuthRoute = pathname === '/login' || pathname === '/register';
  
  if (!token && !isAuthRoute && pathname.startsWith('/chat')) {
    return NextResponse.redirect(new URL('/login', request.url));
  }

  if (token && isAuthRoute) {
    return NextResponse.redirect(new URL('/chat', request.url));
  }

  if (pathname === '/') {
    return NextResponse.redirect(new URL(token ? '/chat' : '/login', request.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: ['/((?!api|_next/static|_next/image|favicon.ico).*)'],
};
