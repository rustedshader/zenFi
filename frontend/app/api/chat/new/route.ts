import { cookies } from 'next/headers'

export const maxDuration = 30

export async function POST(req: Request) {
  try {
    const { message, isDeepSearch } = await req.json()
    const cookieStore = await cookies()
    const token = cookieStore.get('jwt_token')?.value

    if (!token) {
      return new Response('Unauthorized', { status: 401 })
    }

    const response = await fetch(
      `${process.env.NEXT_PUBLIC_BACKEND_API_URL}/chat/new`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({
          message: message,
          isDeepSearch: typeof isDeepSearch !== 'undefined' ? isDeepSearch : false,
        })
      }
    )
    if (!response.ok) {
      const errorText = await response.text()
      console.error('Backend error:', response.status, errorText)
      throw new Error('Network response was not ok')
    }

    return new Response(response.body, {
      headers: {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache',
        Connection: 'keep-alive'
      }
    })
  } catch (error) {
    console.error('API route error:', error)
    return new Response('Error processing your request', { status: 500 })
  }
}
