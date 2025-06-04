// frontend/middleware.ts
import { NextRequest, NextResponse } from 'next/server'

export async function middleware(request: NextRequest) {
  const token = request.cookies.get('jwt_token')?.value
  const pathname = request.nextUrl.pathname

  // Remove validate token part, just check if token exists
  const isValid = !!token
  console.log('Token present:', isValid, 'Pathname:', pathname)

  if (
    !isValid &&
    !pathname.startsWith('/login') &&
    !pathname.startsWith('/register')
  ) {
    console.log('Redirecting to /login')
    return NextResponse.redirect(new URL('/login', request.url))
  }

  return NextResponse.next()
}

export const config = {
  matcher: ['/((?!api|_next/static|_next/image|favicon.ico).*)']
}
