import { cookies } from 'next/headers'
import { NextResponse } from 'next/server'

export async function POST(req: Request) {
  try {
    const { knowledge_base_id } = await req.json()
    console.log('knowledge_base_id:', knowledge_base_id)

    if (!knowledge_base_id) {
      return NextResponse.json(
        {
          error:
            'Missing required fields: knowledge_base_id and query are required'
        },
        { status: 400 }
      )
    }

    const cookieStore = await cookies()
    const token = cookieStore.get('jwt_token')?.value

    if (!token) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const response = await fetch(
      `${process.env.NEXT_PUBLIC_BACKEND_API_URL}/knowledge_base/${knowledge_base_id}/info`,
      {
        method: 'GET',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      }
    )

    if (!response.ok) {
      const errorData = await response.json()
      console.error('Backend error:', response.status, errorData)
      return NextResponse.json(
        { error: errorData.detail || 'Network response was not ok' },
        { status: response.status }
      )
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
