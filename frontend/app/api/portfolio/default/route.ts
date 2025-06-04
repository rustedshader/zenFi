import { cookies } from 'next/headers'
import { NextResponse } from 'next/server'
import { z } from 'zod'

// Define input schema for validation
const requestSchema = z.object({
  portfolio_id: z.string().uuid('Invalid portfolio ID format'),
  set_default: z.boolean({
    invalid_type_error: 'set_default must be a boolean'
  })
})

// Define response types
interface SuccessResponse {
  message: string
  portfolio_id: string
  is_default: boolean
}

interface ErrorResponse {
  error: string
}

export async function POST(req: Request) {
  try {
    // Parse and validate request body
    const body = await req.json()
    const { portfolio_id, set_default } = requestSchema.parse(body)

    // Get JWT token from cookies
    const cookieStore = await cookies()
    const token = cookieStore.get('jwt_token')?.value

    if (!token) {
      return NextResponse.json<ErrorResponse>(
        { error: 'Unauthorized' },
        { status: 401 }
      )
    }

    // Make request to backend API
    const response = await fetch(
      `${process.env.NEXT_PUBLIC_BACKEND_API_URL}/portfolio/${portfolio_id}/default?set_default=${set_default}`,
      {
        method: 'PUT', // Updated to match new backend endpoint
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        }
      }
    )

    if (!response.ok) {
      const errorData = await response.json()
      console.error('Backend error:', response.status, errorData)
      return NextResponse.json<ErrorResponse>(
        {
          error:
            errorData.detail ||
            `Failed to ${set_default ? 'set' : 'remove'} default portfolio`
        },
        { status: response.status }
      )
    }

    const data = await response.json()

    return NextResponse.json<SuccessResponse>(data)
  } catch (error) {
    console.error('API route error:', error)

    // Handle validation errors specifically
    if (error instanceof z.ZodError) {
      return NextResponse.json<ErrorResponse>(
        {
          error: 'Invalid request data'
        },
        { status: 400 }
      )
    }

    return NextResponse.json<ErrorResponse>(
      { error: 'Error processing your request' },
      { status: 500 }
    )
  }
}
