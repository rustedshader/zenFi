import { cookies } from 'next/headers'

export async function GET() {
    try {
        const cookieStore = await cookies()
        const token = cookieStore.get('jwt_token')?.value

        if (!token) {
            return new Response('Unauthorized', { status: 401 })
        }

        const response = await fetch(
            `${process.env.NEXT_PUBLIC_BACKEND_API_URL}/dashboard/stocks`,
            {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                    Authorization: `Bearer ${token}`
                },
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
