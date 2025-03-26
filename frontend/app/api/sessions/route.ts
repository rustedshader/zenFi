// frontend/app/api/sessions/route.ts
import { cookies } from 'next/headers'
import { NextResponse } from 'next/server'

export async function POST(req: Request) {
  const cookieStore = await cookies()
  const token = cookieStore.get('jwt_token')?.value

  if (!token) {
    return new Response('Unauthorized', { status: 401 })
  }

  const response = await fetch(
    `${process.env.NEXT_PUBLIC_BACKEND_API_URL}/sessions`,
    {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json'
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

  const { session_id } = await response.json()
  return NextResponse.json({ session_id })
}
