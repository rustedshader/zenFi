// frontend/components/chat.tsx
'use client'

import { useCallback, useEffect, useState } from 'react'
import { toast } from 'sonner'
import { ChatMessages } from './chat-messages'
import { ChatPanel } from './chat-panel'
import { useAuth } from '@/contexts/auth-context'

interface Message {
  id?: string
  role: 'user' | 'assistant'
  content: string
  sources?: any[]
}

export function Chat({
  id,
  savedMessages = [],
  query
}: {
  id: string
  savedMessages?: Message[]
  query?: string
}) {
  const [messages, setMessages] = useState<Message[]>(savedMessages)
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [sessionId, setSessionId] = useState<string | null>(null)
  const { isLoggedIn } = useAuth()

  useEffect(() => {
    const createSession = async () => {
      const response = await fetch('/api/sessions', { method: 'POST' })
      if (response.ok) {
        const { session_id } = await response.json()
        setSessionId(session_id)
      } else {
        console.error(
          'Session creation failed:',
          response.status,
          await response.text()
        )
        toast.error('Failed to create session')
      }
    }
    if (isLoggedIn && !sessionId) createSession()
  }, [isLoggedIn, sessionId])

  const append = useCallback(
    async (userMessage: string) => {
      if (!sessionId) {
        toast.error('No active session')
        return
      }

      setIsLoading(true)
      const message: Message = {
        role: 'user' as const,
        content: userMessage,
        id: `user-${Date.now()}`
      }
      setMessages(prev => [...prev, message])
      setInput('')

      try {
        const response = await fetch('/api/chat', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ message: userMessage, sessionId })
        })

        if (!response.ok) throw new Error('Network response was not ok')
        // Handle streaming response here...
      } catch (error) {
        console.error('Error sending message:', error)
        toast.error('Error sending message')
        setMessages(prev => prev.slice(0, -1))
        setIsLoading(false)
      }
    },
    [sessionId]
  )

  const stop = () => setIsLoading(false)

  return (
    <div className="relative flex h-[calc(100vh-8rem)] w-full flex-col overflow-hidden">
      <ChatMessages
        messages={messages}
        isLoading={isLoading}
        chatId={id}
        onQuerySelect={() => {}}
      />
      <ChatPanel
        input={input}
        handleInputChange={e => setInput(e.target.value)}
        handleSubmit={e => {
          e.preventDefault()
          if (input.trim()) append(input)
        }}
        isLoading={isLoading}
        messages={messages}
        setMessages={setMessages}
        query={query}
        stop={stop}
        append={append}
      />
    </div>
  )
}
