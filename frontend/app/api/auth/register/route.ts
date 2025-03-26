// frontend/app/api/auth/register/route.ts
import { NextResponse } from 'next/server'

export async function POST(req: Request) {
  const { username, email, password } = await req.json()

  const response = await fetch(
    `${process.env.NEXT_PUBLIC_BACKEND_API_URL}/register`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, email, password })
    }
  )

  if (!response.ok) {
    const error = await response.json()
    return NextResponse.json(
      { error: error.detail },
      { status: response.status }
    )
  }

  const data = await response.json()
  return NextResponse.json(data)
}
