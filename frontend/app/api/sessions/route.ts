// /frontend/app/api/sessions/route.ts
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
    let errorDetail: unknown
    try {
      const clonedResponse = response.clone()
      const errorJson = await clonedResponse.json()
      errorDetail = errorJson.detail || errorJson
    } catch (e) {
      const clonedResponse = response.clone()
      errorDetail = await clonedResponse.text()
    }
    return NextResponse.json(
      { error: errorDetail },
      { status: response.status }
    )
  }

  const { session_id } = await response.json()
  return NextResponse.json({ session_id })
}
