import { cookies } from 'next/headers'
import { NextResponse } from 'next/server'

export async function POST(req: Request) {
  try {
    const formData = await req.formData()
    const knowledge_base_id = formData.get('knowledge_base_id') as string
    const chunk_size = formData.get('chunk_size') as string
    const overlap = formData.get('overlap') as string
    const file = formData.get('file') as File
    const url = formData.get('url') as string

    // Validate that either file or URL is provided, but not both
    if (!knowledge_base_id || (!file && !url) || (file && url)) {
      return NextResponse.json(
        {
          error:
            'Missing or invalid fields: knowledge_base_id is required, and provide either a file or a URL, but not both'
        },
        { status: 400 }
      )
    }

    // Validate file type if provided
    if (file && !file.type.includes('pdf')) {
      return NextResponse.json(
        { error: 'Only PDF files are supported' },
        { status: 400 }
      )
    }

    // Validate URL format if provided
    if (url) {
      try {
        new URL(url)
      } catch {
        return NextResponse.json(
          { error: 'Invalid URL format' },
          { status: 400 }
        )
      }
    }

    const cookieStore = await cookies()
    const token = cookieStore.get('jwt_token')?.value

    if (!token) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const uploadFormData = new FormData()
    uploadFormData.append('knowledge_base_id', knowledge_base_id)
    if (chunk_size) uploadFormData.append('chunk_size', chunk_size)
    if (overlap) uploadFormData.append('overlap', overlap)
    if (file) uploadFormData.append('file', file)
    if (url) uploadFormData.append('url', url)

    const response = await fetch(
      `${process.env.NEXT_PUBLIC_BACKEND_API_URL}/knowledge_base/${knowledge_base_id}/upload`,
      {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`
        },
        body: uploadFormData
      }
    )

    if (!response.ok) {
      const errorData = await response.json()
      console.error('Backend error:', response.status, errorData)
      return NextResponse.json(
        { error: errorData.detail || 'Failed to process request' },
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
