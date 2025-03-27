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
    <div className="p-4">
      <h1 className="text-xl font-bold mb-4">Your Chat Sessions</h1>
      {sessions.length === 0 ? (
        <p>No sessions found.</p>
      ) : (
        <ul>
          {sessions.map(session => (
            <li key={session.session_id} className="mb-2">
              <Button
                variant="link"
                onClick={() => router.push(`/chat/${session.session_id}`)}
              >
                Session from {new Date(session.created_at).toLocaleString()}
              </Button>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
