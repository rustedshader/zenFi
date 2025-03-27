import { NextResponse } from 'next/server'
import { cookies } from 'next/headers'

export async function GET(request: Request) {
  const cookieStore = await cookies()
  const token = cookieStore.get('jwt_token')?.value
  if (!token) {
    return new Response('Unauthorized', { status: 401 })
  }
  const response = await fetch(
    `${process.env.NEXT_PUBLIC_BACKEND_API_URL}/sessions`,
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
  const sessions = await response.json()
  return NextResponse.json(sessions)
}
