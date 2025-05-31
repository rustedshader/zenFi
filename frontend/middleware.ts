// frontend/middleware.ts
import { NextRequest, NextResponse } from 'next/server';

export async function middleware(request: NextRequest) {
  const token = request.cookies.get('jwt_token')?.value;
  const pathname = request.nextUrl.pathname;

  async function isValidCheck(token?: string): Promise<boolean> {
    if (!token) {
      console.log('No token found');
      return false;
    }
    try {
      console.log('Validating token with backend:', process.env.NEXT_PUBLIC_BACKEND_API_URL);
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_BACKEND_API_URL}/auth/validate_token`,
        {
          method: 'POST',
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );
      if (!response.ok) {
        console.log('Token validation failed with status:', response.status);
      }
      return response.ok;
    } catch (error) {
      console.error('Token validation error:', error);
      return false;
    }
  }

  const isValid = await isValidCheck(token);
  console.log('Token valid:', isValid, 'Pathname:', pathname);

  if (
    !isValid &&
    !pathname.startsWith('/login') &&
    !pathname.startsWith('/register')
  ) {
    console.log('Redirecting to /login');
    return NextResponse.redirect(new URL('/login', request.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: ['/((?!api|_next/static|_next/image|favicon.ico).*)'],
};