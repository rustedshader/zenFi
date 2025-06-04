import { cookies } from 'next/headers'
import { NextResponse } from 'next/server'

export async function POST(request: Request) {
  try {
    const { username, password } = await request.json()

    // Validate input before sending request
    if (!username || !password) {
      return NextResponse.json(
        { error: 'Username and password are required' },
        { status: 400 }
      )
    }

    // Create form data for OAuth2PasswordRequestForm
    const formData = new URLSearchParams()
    formData.append('username', username)
    formData.append('password', password)

    const response = await fetch(
      `${process.env.NEXT_PUBLIC_BACKEND_API_URL}/auth/login`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded'
        },
        body: formData.toString()
      }
    )

    if (!response.ok) {
      const errorData = await response.json()

      // Handle backend validation errors
      if (errorData.error && Array.isArray(errorData.error)) {
        const errorMessages = errorData.error
          .map((err: { msg: string }) => err.msg)
          .join(', ')
        return NextResponse.json(
          { error: errorMessages || 'Authentication failed' },
          { status: response.status }
        )
      }

      // Handle other errors (e.g., incorrect credentials)
      return NextResponse.json(
        { error: errorData.detail || 'Authentication failed' },
        { status: response.status }
      )
    }

    const data = await response.json()
    const cookieStore = await cookies()

    // Store access token
    cookieStore.set('access_token', data.access_token, {
      httpOnly: true,
      secure: true,
      sameSite: 'strict',
      maxAge: 3600, // 1 hour in seconds
      path: '/'
    })

    // Store refresh token
    cookieStore.set('refresh_token', data.refresh_token, {
      httpOnly: true,
      secure: true,
      sameSite: 'strict',
      maxAge: 86400, // 1 day in seconds
      path: '/'
    })

    return NextResponse.json({
      message: 'Login successful',
      token_type: data.token_type
    })
  } catch (error) {
    console.error('Login error:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}
