import { cookies } from 'next/headers'
import { NextResponse } from 'next/server'

export async function POST(req: Request) {
  try {
    const body = await req.json()
    const { knowledge_base_id, query, max_results, filter } = body

    if (!knowledge_base_id || !query) {
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

    const payload = {
      query,
      max_results: max_results || 5,
      ...(filter && { filter })
    }

    const response = await fetch(
      `${process.env.NEXT_PUBLIC_BACKEND_API_URL}/knowledge_base/${knowledge_base_id}/query`,
      {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(payload)
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
