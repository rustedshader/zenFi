import { cookies } from 'next/headers'

export async function PUT(_: Request, { params }: { params: { portfolio_id: number , asset_id: number } }) {
    try {
        const portfolio_id = await params.portfolio_id
        const asset_id = await params.asset_id
        const {asset_type,identifier,quantity,purchase_price,purchase_date} = await _.json()
        const cookieStore = await cookies()
        const token = cookieStore.get('jwt_token')?.value

        if (!token) {
            return new Response('Unauthorized', { status: 401 })
        }

        const response = await fetch(
            `${process.env.NEXT_PUBLIC_BACKEND_API_URL}/portfolio/${portfolio_id}/assests/${asset_id}`,
            {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                    Authorization: `Bearer ${token}`
                },
                body: JSON.stringify({asset_type,identifier,quantity,purchase_price,purchase_date})
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
