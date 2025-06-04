import { cookies } from 'next/headers'
import { NextResponse } from 'next/server'

export async function POST(req: Request) {
  try {
    const { portfolio_id } = await req.json()
    const cookieStore = await cookies()
    const token = cookieStore.get('jwt_token')?.value

    if (!token) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const response = await fetch(
      `${process.env.NEXT_PUBLIC_BACKEND_API_URL}/portfolio/${portfolio_id}/ai_summary`,
      {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        }
      }
    )

    if (!response.ok) {
      const errorText = await response.text()
      console.error('Backend error:', response.status, errorText)
      throw new Error('Network response was not ok')
    }

    const data = await response.json()

    return NextResponse.json(data)
  } catch (error) {
    console.error('API route error:', error)
    return NextResponse.json(
      { error: 'Error processing your request' },
      { status: 500 }
    )
  }
}
