'use client'
import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle
} from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Separator } from '@/components/ui/separator'
import { toast } from 'sonner'
import {
  Clock,
  MessageSquare,
  Loader2,
  ArrowRight,
  Plus,
  History
} from 'lucide-react'

type Session = {
  session_id: string
  created_at: string
  summary?: string
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

  const getRelativeTime = (dateString: string) => {
    const date = new Date(dateString)
    const now = new Date()
    const diffInHours = Math.floor(
      (now.getTime() - date.getTime()) / (1000 * 60 * 60)
    )

    if (diffInHours < 1) return 'Just now'
    if (diffInHours < 24) return `${diffInHours}h ago`
    if (diffInHours < 168) return `${Math.floor(diffInHours / 24)}d ago`
    return `${Math.floor(diffInHours / 168)}w ago`
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
    <div className="container mx-auto px-4 py-8 max-w-4xl">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-8">
        <div className="space-y-1">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-primary/10">
              <History className="h-6 w-6 text-primary" />
            </div>
            <h1 className="text-3xl font-bold tracking-tight">Chat History</h1>
          </div>
          <p className="text-muted-foreground">
            Browse and continue your previous conversations
          </p>
        </div>
        <Button onClick={() => router.push('/')} className="gap-2" size="lg">
          <Plus className="h-4 w-4" />
          New Chat
        </Button>
      </div>

      <Separator className="mb-8" />

      {/* Content */}
      {isLoading ? (
        <div className="flex flex-col items-center justify-center py-16">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground mb-4" />
          <p className="text-muted-foreground text-lg">
            Loading your conversations...
          </p>
        </div>
      ) : sessions.length === 0 ? (
        <Card className="text-center py-16">
          <CardContent className="space-y-4">
            <div className="mx-auto w-16 h-16 rounded-full bg-muted flex items-center justify-center">
              <MessageSquare className="h-8 w-8 text-muted-foreground" />
            </div>
            <div className="space-y-2">
              <h3 className="text-xl font-semibold">No conversations yet</h3>
              <p className="text-muted-foreground">
                Start your first chat conversation to see it appear here
              </p>
            </div>
            <Button
              onClick={() => router.push('/chat')}
              variant="outline"
              className="gap-2"
            >
              <Plus className="h-4 w-4" />
              Start a New Chat
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-4">
          {sessions.map((session, index) => (
            <Card
              key={session.session_id}
              className="cursor-pointer transition-all duration-200 hover:shadow-md hover:scale-[1.01] group"
              onClick={() => router.push(`/chat/${session.session_id}`)}
            >
              <CardHeader className="pb-3">
                <div className="flex items-start justify-between">
                  <div className="flex items-start gap-3 flex-1 min-w-0">
                    <div className="p-2 rounded-lg bg-primary/10 mt-1 flex-shrink-0">
                      <MessageSquare className="h-5 w-5 text-primary" />
                    </div>
                    <div className="flex-1 min-w-0 space-y-1">
                      <div className="flex items-center gap-2">
                        <CardTitle className="text-lg">
                          {session.summary || 'Chat Conversation'}
                        </CardTitle>
                        {index === 0 && (
                          <Badge variant="secondary" className="text-xs">
                            Latest
                          </Badge>
                        )}
                      </div>
                      <div className="flex items-center gap-4 text-sm text-muted-foreground">
                        <div className="flex items-center gap-1">
                          <Clock className="h-4 w-4" />
                          <span>{getRelativeTime(session.created_at)}</span>
                        </div>
                        <span className="hidden sm:inline">
                          {formatDate(session.created_at)}
                        </span>
                      </div>
                    </div>
                  </div>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0"
                  >
                    <ArrowRight className="h-4 w-4" />
                  </Button>
                </div>
              </CardHeader>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
