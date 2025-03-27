// frontend/app/api/auth/login/route.ts
import { cookies } from 'next/headers'
import { NextResponse } from 'next/server'

export async function POST(req: Request) {
  const { username, password } = await req.json()

  const response = await fetch(
    `${process.env.NEXT_PUBLIC_BACKEND_API_URL}/login`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password })
    }
  )

  console.log(response)

  if (!response.ok) {
    const error = await response.json()
    return NextResponse.json(
      { error: error.detail },
      { status: response.status }
    )
  }

  const data = await response.json()
  const cookieStore = await cookies()
  cookieStore.set('jwt_token', data.access_token, {
    httpOnly: false,
    secure: true,
    maxAge: 3600
  })
  return NextResponse.json({ message: 'Login successful' })
}
