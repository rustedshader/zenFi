'use client'
import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { Button } from '@/components/ui/button'
import { toast } from 'sonner'

type Session = {
  session_id: string
  created_at: string
}

export default function SessionsPage() {
  const [sessions, setSessions] = useState<Session[]>([])
  const router = useRouter()

  useEffect(() => {
    async function fetchSessions() {
      try {
        const res = await fetch('/api/sessions/list')
        if (res.ok) {
          const data = await res.json()
          setSessions(data)
        } else {
          toast.error('Failed to load sessions')
        }
      } catch (error) {
        console.error(error)
        toast.error('Error loading sessions')
      }
    }
    fetchSessions()
  }, [])

  return (
    <div className="p-4 max-w-4xl mx-auto">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">Your Chat Sessions</h1>
        <Button
          onClick={() => router.push('/')}
          className="bg-blue-500 hover:bg-blue-600 text-white"
        >
          New Chat
        </Button>
      </div>
      {sessions.length === 0 ? (
        <div className="text-center py-8">
          <p className="text-gray-500 mb-4">No chat sessions found.</p>
          <Button onClick={() => router.push('/chat')} variant="outline">
            Start a New Chat
          </Button>
        </div>
      ) : (
        <div className="space-y-2">
          {sessions.map(session => (
            <div
              key={session.session_id}
              className="p-4 rounded-lg border border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
            >
              <Button
                variant="ghost"
                className="w-full text-left justify-start"
                onClick={() => router.push(`/chat/${session.session_id}`)}
              >
                <div className="flex flex-col items-start">
                  <span className="font-medium">Chat Session</span>
                  <span className="text-sm text-gray-500 dark:text-gray-400">
                    {new Date(session.created_at).toLocaleString()}
                  </span>
                </div>
              </Button>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
