// frontend/middleware.ts
import { NextRequest, NextResponse } from 'next/server'

export async function middleware(request: NextRequest) {
  const token = request.cookies.get('jwt_token')?.value
  const pathname = request.nextUrl.pathname

  // Skip middleware for login, register, or static assets
  if (
    pathname.startsWith('/login') ||
    pathname.startsWith('/register') ||
    pathname.startsWith('/_next') ||
    pathname === '/favicon.ico'
  ) {
    return NextResponse.next()
  }

  // If no token, redirect to login
  if (!token) {
    console.log('No token found, redirecting to /login')
    return NextResponse.redirect(new URL('/login', request.url))
  }

  // Validate token expiration (client-side decoding)
  try {
    const payload = JSON.parse(atob(token.split('.')[1]))
    const expirationTime = payload.exp * 1000 // Convert to milliseconds
    const currentTime = Date.now()

    if (currentTime >= expirationTime) {
      console.log('Token expired, clearing cookie and redirecting to /login')
      // Clear the token cookie
      const response = NextResponse.redirect(new URL('/login', request.url))
      response.cookies.delete('jwt_token')
      return response
    }
  } catch (error) {
    console.error('Error decoding token:', error)
    // If token is malformed or invalid, treat as expired
    const response = NextResponse.redirect(new URL('/login', request.url))
    response.cookies.delete('jwt_token')
    return response
  }

  // Optional: Validate token with backend for critical routes
  /*
  try {
    const validationResponse = await fetch(
      `${process.env.NEXT_PUBLIC_BACKEND_API_URL}/auth/validate`,
      {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
        },
      }
    );

    if (!validationResponse.ok) {
      console.log('Token invalid on backend, clearing cookie and redirecting to /login');
      const response = NextResponse.redirect(new URL('/login', request.url));
      response.cookies.delete('jwt_token');
      return response;
    }
  } catch (error) {
    console.error('Error validating token with backend:', error);
    const response = NextResponse.redirect(new URL('/login', request.url));
    response.cookies.delete('jwt_token');
    return response;
  }
  */

  console.log('Token valid, proceeding to:', pathname)
  return NextResponse.next()
}

export const config = {
  matcher: ['/((?!api|_next/static|_next/image|images|favicon.ico).*)']
}
