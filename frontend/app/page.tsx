// frontend/app/page.tsx
'use client'

import { useAuth } from '@/contexts/auth-context'
import { useRouter } from 'next/navigation'
import { useEffect, useState } from 'react'
import Textarea from 'react-textarea-autosize'
import { toast } from 'sonner'

export default function Page() {
  const router = useRouter()
  const [error, setError] = useState<string | null>(null)
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const { isLoggedIn, isLoading: isAuthLoading } = useAuth()

  useEffect(() => {
    if (!isAuthLoading && !isLoggedIn) {
      router.push('/login')
    }
  }, [router, isLoggedIn, isAuthLoading])

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    if (!input.trim()) return

    setIsLoading(true)
    try {
      // Create session first
      const response = await fetch('/api/sessions/init', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: input.trim() })
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.error || 'Failed to create session')
      }

      const data = await response.json()

      // Redirect with both session ID and query
      router.push(
        `/chat/${data.session_id}?query=${encodeURIComponent(input.trim())}`
      )
    } catch (error) {
      console.error('Error:', error)
      setError('Failed to initialize chat. Please try again later.')
      toast.error('Failed to create chat session')
      router.push('/')
    } finally {
      setIsLoading(false)
    }
  }

  if (isAuthLoading) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center p-24">
        <div className="w-full max-w-md space-y-8">
          <div className="text-center">
            <h1 className="text-2xl font-bold">Loading...</h1>
            <p className="mt-2 text-gray-600">
              Please wait while we check your authentication status.
            </p>
          </div>
        </div>
      </div>
    )
  }

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
    <div className="flex min-h-screen flex-col">
      <div className="flex-1 flex items-center justify-center p-24">
        <div className="w-full max-w-3xl space-y-8">
          <div className="text-center">
            <h1 className="text-2xl font-bold">Welcome to Zenfi AI</h1>
            <p className="mt-2 text-gray-600">Start your finance journey ! </p>
          </div>
        </div>
      </div>
      <div className="fixed bottom-0 left-0 w-full">
        <div className="mx-auto max-w-3xl px-2 sm:px-4 pb-4 sm:pb-6">
          <form onSubmit={handleSubmit} className="relative">
            <div className="relative rounded-2xl bg-white border border-gray-200 shadow-sm overflow-hidden">
              <Textarea
                name="input"
                rows={2}
                maxRows={6}
                placeholder="How can I help?"
                value={input}
                onChange={e => setInput(e.target.value)}
                className="w-full resize-none bg-transparent text-gray-900 placeholder:text-gray-500 focus:outline-none py-3 sm:py-5 px-3 sm:px-5 pr-12 text-sm sm:text-base"
                onKeyDown={e => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault()
                    const form = e.currentTarget.form
                    if (form) {
                      form.requestSubmit()
                    }
                  }
                }}
              />
              <button
                type="submit"
                disabled={isLoading || input.trim().length === 0}
                className="absolute right-1 sm:right-2 bottom-1 sm:bottom-2 bg-transparent hover:bg-gray-100 text-gray-600 hover:text-gray-900 rounded-lg p-1.5 sm:p-2 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  width="24"
                  height="24"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  className="size-4 sm:size-5"
                >
                  <path d="M5 12h14" />
                  <path d="m12 5 7 7-7 7" />
                </svg>
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  )
}
