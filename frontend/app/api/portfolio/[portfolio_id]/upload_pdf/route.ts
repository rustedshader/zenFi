import { cookies } from 'next/headers'
import { NextResponse } from 'next/server'

export async function POST(
  req: Request,
  { params }: { params: { portfolio_id: string } }
) {
  try {
    const portfolio_id = await params.portfolio_id
    const cookieStore = await cookies()
    const token = cookieStore.get('jwt_token')?.value

    if (!token) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const formData = await req.formData()

    if (!formData.has('file')) {
      return NextResponse.json({ error: 'No file provided' }, { status: 400 })
    }

    const response = await fetch(
      `${process.env.NEXT_PUBLIC_BACKEND_API_URL}/portfolio/${portfolio_id}/upload_pdf`,
      {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`
        },
        body: formData
      }
    )

    if (!response.ok) {
      const errorText = await response.text()
      console.error('Backend error:', response.status, errorText)
      return NextResponse.json(
        { error: errorText },
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
