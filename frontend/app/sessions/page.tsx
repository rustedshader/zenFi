'use client'
import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { Button } from '@/components/ui/button'
import { toast } from 'sonner'
import { Clock, MessageSquare, Loader2 } from 'lucide-react'

type Session = {
  session_id: string
  created_at: string
}

export default function SessionsPage() {
  const [sessions, setSessions] = useState<Session[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const router = useRouter()

  const formatDate = (dateString: string) => {
    const date = new Date(dateString)
    const localDate = new Date(
      date.getTime() - date.getTimezoneOffset() * 60000
    )
    return localDate.toLocaleString(undefined, {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      hour12: true
    })
  }

  useEffect(() => {
    async function fetchSessions() {
      try {
        setIsLoading(true)
        const res = await fetch('/api/sessions/list')
        if (res.ok) {
          const data = await res.json()
          // Sort sessions by created_at in descending order (newest first)
          const sortedSessions = data.sort(
            (a: Session, b: Session) =>
              new Date(b.created_at).getTime() -
              new Date(a.created_at).getTime()
          )
          setSessions(sortedSessions)
        } else {
          toast.error('Failed to load history')
        }
      } catch (error) {
        console.error(error)
        toast.error('Error loading history')
      } finally {
        setIsLoading(false)
      }
    }
    fetchSessions()
  }, [])

  return (
    <div className="p-4 max-w-4xl mx-auto">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-6">
        <div className="flex items-center gap-2">
          <MessageSquare className="size-6" />
          <h1 className="text-2xl font-bold">Chat History</h1>
        </div>
        <Button
          onClick={() => router.push('/')}
          className="w-full sm:w-auto bg-black hover:bg-gray-800 text-white"
        >
          New Chat
        </Button>
      </div>
      {isLoading ? (
        <div className="flex flex-col items-center justify-center py-12">
          <Loader2 className="size-8 animate-spin text-gray-400 mb-4" />
          <p className="text-gray-500">Loading chat history...</p>
        </div>
      ) : sessions.length === 0 ? (
        <div className="text-center py-12">
          <div className="mb-4">
            <MessageSquare className="size-12 mx-auto text-gray-400" />
          </div>
          <p className="text-gray-500 mb-4">No chat history found.</p>
          <Button onClick={() => router.push('/chat')} variant="outline">
            Start a New Chat
          </Button>
        </div>
      ) : (
        <div className="space-y-3">
          {sessions.map(session => (
            <div
              key={session.session_id}
              className="p-4 rounded-lg border border-gray-200 hover:bg-gray-50 transition-colors cursor-pointer"
              onClick={() => router.push(`/chat/${session.session_id}`)}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded-full bg-gray-100">
                    <MessageSquare className="size-5 text-gray-900" />
                  </div>
                  <div className="flex flex-col">
                    <span className="font-medium">Chat Conversation</span>
                    <div className="flex items-center gap-1 text-sm text-gray-500">
                      <Clock className="size-4" />
                      <span>{formatDate(session.created_at)}</span>
                    </div>
                  </div>
                </div>
                <Button
                  variant="ghost"
                  size="icon"
                  className="text-gray-400 hover:text-gray-900"
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
                    className="size-4"
                  >
                    <path d="m9 18 6-6-6-6" />
                  </svg>
                </Button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
