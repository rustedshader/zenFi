// frontend/middleware.ts
import { NextRequest, NextResponse } from 'next/server'

export async function middleware(request: NextRequest) {
  const token = request.cookies.get('jwt_token')?.value
  const pathname = request.nextUrl.pathname

  async function isValidCheck(token?: string): Promise<boolean> {
    const response = await fetch(
      `${process.env.NEXT_PUBLIC_BACKEND_API_URL}/auth/validate_token`,
      {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`
        }
      }
    )
    return response.ok
  }

  const isValid = await isValidCheck(token)

  if (
    !isValid &&
    !pathname.startsWith('/login') &&
    !pathname.startsWith('/register')
  ) {
    return NextResponse.redirect(new URL('/login', request.url))
  }

  return NextResponse.next()
}

export const config = {
  matcher: ['/((?!api|_next/static|_next/image|favicon.ico).*)']
}
