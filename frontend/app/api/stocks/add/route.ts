import { cookies } from 'next/headers'
import { NextResponse } from 'next/server'

export async function POST(req: Request) {
    try {
        const { sessionId, stock_symbol } = await req.json()
        const cookieStore = await cookies()
        const token = cookieStore.get('jwt_token')?.value

        if (!token) {
            return new Response('Unauthorized', { status: 401 })
        }

        if (!sessionId) {
            return new Response('Session ID required', { status: 400 })
        }

        const response = await fetch(
            `${process.env.NEXT_PUBLIC_BACKEND_API_URL}/stock/add`,
            {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    Authorization: `Bearer ${token}`
                },
                body: JSON.stringify({
                    session_id: sessionId,
                    stock_symbol: stock_symbol,
                })
            }
        )

        if (!response.ok) {
            const errorText = await response.text()
            console.error('Backend error:', response.status, errorText)
            throw new Error('Network response was not ok')
        }

        return new Response(response.body)
    } catch (error) {
        console.error('API route error:', error)
        return new Response('Error processing your request', { status: 500 })
    }
}
