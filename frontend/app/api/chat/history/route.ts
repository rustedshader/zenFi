import { NextResponse } from 'next/server'
import { cookies } from 'next/headers'

export async function GET(request: Request) {
  const cookieStore = await cookies()
  const token = cookieStore.get('jwt_token')?.value
  if (!token) {
    return new Response('Unauthorized', { status: 401 })
  }

  // Get sessionId from URL
  const { searchParams } = new URL(request.url)
  const sessionId = searchParams.get('sessionId')

  if (!sessionId) {
    return NextResponse.json(
      { error: 'Session ID is required' },
      { status: 400 }
    )
  }

  const response = await fetch(
    `${process.env.NEXT_PUBLIC_BACKEND_API_URL}/chat/history?session_id=${sessionId}`,
    {
      method: 'GET',
      headers: {
        Authorization: `Bearer ${token}`
      }
    }
  )

  if (!response.ok) {
    const error = await response.json()
    return NextResponse.json(
      { error: error.detail },
      { status: response.status }
    )
  }

  const history = await response.json()
  return NextResponse.json(history)
}
