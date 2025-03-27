'use client'

import { useAuth } from '@/contexts/auth-context'
import { useRouter } from 'next/navigation'
import { useEffect, useState } from 'react'
import { toast } from 'sonner'

// TODO When Someone Visits This Page Take Query in Input Field then redirect them to /chat/[sessionId]

export default function Page() {
  const router = useRouter()
  const [error, setError] = useState<string | null>(null)
  const { isLoggedIn } = useAuth()

  useEffect(() => {
    const createSession = async () => {
      try {
        if (!isLoggedIn) {
          router.push('/login')
          return
        }

        const response = await fetch('/api/sessions', {
          method: 'POST'
        })

        if (!response.ok) {
          const errorData = await response.json()
          throw new Error(errorData.error || 'Failed to create session')
        }

        const data = await response.json()
        router.push(`/chat/${data.session_id}`)
      } catch (error) {
        console.error('Error:', error)
        setError('Failed to initialize chat. Please try again later.')
        toast.error('Failed to create chat session')
      }
    }

    createSession()
  }, [router, isLoggedIn])

  if (error) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center p-24">
        <div className="w-full max-w-md space-y-8">
          <div className="text-center">
            <h1 className="text-2xl font-bold text-red-600">Error</h1>
            <p className="mt-2 text-gray-600">{error}</p>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="flex min-h-screen flex-col items-center justify-center p-24">
      <div className="w-full max-w-md space-y-8">
        <div className="text-center">
          <h1 className="text-2xl font-bold">Welcome to Chat</h1>
          <p className="mt-2 text-gray-600">Creating your chat session...</p>
        </div>
      </div>
    </div>
  )
}
