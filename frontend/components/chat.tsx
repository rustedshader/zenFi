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
  timestamp?: number
}

interface ChatProps {
  id: string
  savedMessages?: Message[]
  query?: string
  sessionId?: string
}

export function Chat({
  id,
  savedMessages = [],
  query,
  sessionId: initialSessionId
}: ChatProps) {
  const [messages, setMessages] = useState<Message[]>(savedMessages)
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  // Use provided sessionId if available; otherwise null so that we create a new session
  const [sessionId, setSessionId] = useState<string | null>(
    initialSessionId || null
  )
  const { isLoggedIn, logout } = useAuth()

  useEffect(() => {
    async function createSession() {
      try {
        const response = await fetch('/api/sessions', { method: 'POST' })
        if (response.ok) {
          const data = await response.json()
          setSessionId(data.session_id)
        } else if (response.status === 401) {
          logout()
          toast.error('Session expired. Please login again.')
        } else {
          console.error(
            'Session creation failed:',
            response.status,
            await response.text()
          )
          toast.error('Failed to create session')
        }
      } catch (error) {
        console.error(error)
        toast.error('Error creating session')
      }
    }
    if (isLoggedIn && !sessionId) {
      createSession()
    }
  }, [isLoggedIn, sessionId, logout])

  useEffect(() => {
    async function fetchChatHistory() {
      if (!sessionId) return

      try {
        const response = await fetch(`/api/chat/history?sessionId=${sessionId}`)
        if (!response.ok) {
          if (response.status === 401) {
            logout()
            toast.error('Session expired. Please login again.')
            return
          }
          throw new Error('Failed to fetch chat history')
        }
        const history = await response.json()
        setMessages(history)
      } catch (error) {
        console.error('Error fetching chat history:', error)
        toast.error('Failed to load chat history')
      }
    }

    fetchChatHistory()
  }, [sessionId, logout])

  const append = useCallback(
    async (userMessage: Message) => {
      if (!sessionId) {
        toast.error('No active session')
        return
      }

      setIsLoading(true)
      // Append the user message
      setMessages(prev => [...prev, userMessage])
      setInput('')

      try {
        const response = await fetch('/api/chat', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          // Note: the API route translates "sessionId" into the backend's expected "session_id" field.
          body: JSON.stringify({ message: userMessage.content, sessionId })
        })

        if (!response.ok) {
          if (response.status === 401) {
            logout()
            toast.error('Session expired. Please login again.')
            return
          }
          throw new Error('Network response was not ok')
        }

        const reader = response.body?.getReader()
        if (reader) {
          const decoder = new TextDecoder()
          let assistantMessage: Message = {
            role: 'assistant',
            content: '',
            id: `assistant-${Date.now()}`,
            timestamp: Date.now()
          }
          // Don't add the assistant message immediately
          let hasAddedAssistantMessage = false

          let buffer = ''
          while (true) {
            const { done, value } = await reader.read()
            if (done) break

            buffer += decoder.decode(value, { stream: true })
            const lines = buffer.split('\n')
            buffer = lines.pop() || ''

            for (const line of lines) {
              if (line.trim().startsWith('data:')) {
                const jsonStr = line.replace(/^data:\s*/, '')
                try {
                  const parsed = JSON.parse(jsonStr)
                  if (parsed.type === 'complete') {
                    setIsLoading(false)
                    break
                  }
                  if (parsed.content) {
                    if (!hasAddedAssistantMessage) {
                      setMessages(prev => [...prev, assistantMessage])
                      hasAddedAssistantMessage = true
                    }
                    assistantMessage.content += parsed.content
                    setMessages(prev => {
                      const updated = [...prev]
                      updated[updated.length - 1] = { ...assistantMessage }
                      return updated
                    })
                  }
                } catch (err) {
                  console.error('Error parsing JSON:', err)
                }
              }
            }
          }
        }
      } catch (error) {
        console.error('Error sending message:', error)
        toast.error('Error sending message')
        setMessages(prev => prev.slice(0, -1))
        setIsLoading(false)
      }
    },
    [sessionId, logout]
  )

  const stop = () => setIsLoading(false)

  return (
    <div className="flex flex-col h-[calc(100vh-4rem)]">
      <div className="flex-1 overflow-y-auto pb-32">
        <ChatMessages
          messages={messages}
          isLoading={isLoading}
          chatId={id}
          onQuerySelect={() => {}}
        />
      </div>
      <ChatPanel
        input={input}
        handleInputChange={e => setInput(e.target.value)}
        handleSubmit={e => {
          e.preventDefault()
          if (input.trim()) {
            append({
              role: 'user',
              content: input,
              id: `user-${Date.now()}`
            })
          }
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
