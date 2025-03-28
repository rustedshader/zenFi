// frontend/app/api/sessions/init/route.ts
import { cookies } from 'next/headers'
import { NextResponse } from 'next/server'

export async function POST(req: Request) {
  const cookieStore = await cookies()
  const token = cookieStore.get('jwt_token')?.value
  if (!token) {
    return new Response('Unauthorized', { status: 401 })
  }

  const { query } = await req.json()
  if (!query || !query.trim()) {
    return NextResponse.json(
      { error: 'Query cannot be empty' },
      { status: 400 }
    )
  }

  // Create a new session by calling the backend sessions endpoint
  const sessionResponse = await fetch(
    `${process.env.NEXT_PUBLIC_BACKEND_API_URL}/sessions`,
    {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}` }
    }
  )

  if (!sessionResponse.ok) {
    const error = await sessionResponse.json()
    return NextResponse.json(
      { error: error.detail },
      { status: sessionResponse.status }
    )
  }

  const sessionData = await sessionResponse.json()
  const sessionId = sessionData.session_id

  // Return both session id and query
  return NextResponse.json({
    session_id: sessionId,
    query: query
  })
}
