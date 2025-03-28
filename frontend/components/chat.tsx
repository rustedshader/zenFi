'use client'

import { useAuth } from '@/contexts/auth-context'
import { useCallback, useEffect, useRef, useState } from 'react'
import { toast } from 'sonner'
import { ChatMessages } from './chat-messages'
import { ChatPanel } from './chat-panel'

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
  sessionId?: string
  initialQuery?: string
}

export function Chat({
  id,
  savedMessages = [],
  sessionId: initialSessionId,
  initialQuery
}: ChatProps) {
  const [messages, setMessages] = useState<Message[]>(savedMessages)
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [sessionId, setSessionId] = useState<string | null>(
    initialSessionId || null
  )
  const { isLoggedIn, logout } = useAuth()
  const initializedRef = useRef(false)

  // Combined effect for session creation and initial query
  useEffect(() => {
    async function initializeChat() {
      if (!isLoggedIn || initializedRef.current) return

      try {
        initializedRef.current = true

        // Only create session if we don't have one
        if (!sessionId) {
          const response = await fetch('/api/sessions', { method: 'POST' })
          if (!response.ok) {
            if (response.status === 401) {
              logout()
              toast.error('Session expired. Please login again.')
              return
            }
            throw new Error('Failed to create session')
          }
          const data = await response.json()
          setSessionId(data.session_id)
        }

        // Fetch chat history if we have a session
        if (sessionId) {
          const historyResponse = await fetch(
            `/api/chat/history?sessionId=${sessionId}`
          )
          if (!historyResponse.ok) {
            if (historyResponse.status === 401) {
              logout()
              toast.error('Session expired. Please login again.')
              return
            }
            throw new Error('Failed to fetch chat history')
          }
          const history = await historyResponse.json()
          setMessages(history)

          // Handle initial query after history is loaded
          if (initialQuery && history.length === 0) {
            const userMessage: Message = {
              role: 'user',
              content: initialQuery,
              id: `user-${Date.now()}-${Math.random()
                .toString(36)
                .substring(2, 9)}`,
              timestamp: Date.now()
            }
            append(userMessage)
          }
        }
      } catch (error) {
        console.error('Error initializing chat:', error)
        toast.error('Failed to initialize chat')
        initializedRef.current = false // Reset on error
      }
    }

    initializeChat()
  }, [isLoggedIn, initialQuery, logout]) // Removed sessionId from dependencies

  const append = useCallback(
    async (userMessage: Message) => {
      if (!sessionId) {
        toast.error('No active session')
        return
      }

      setIsLoading(true)
      setMessages(prev => [...prev, userMessage])
      setInput('')

      try {
        const response = await fetch('/api/chat', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
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
            id: `assistant-${Date.now()}-${Math.random()
              .toString(36)
              .substring(2, 9)}`,
            timestamp: Date.now()
          }
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
              id: `user-${Date.now()}-${Math.random()
                .toString(36)
                .substring(2, 9)}`
            })
          }
        }}
        isLoading={isLoading}
        messages={messages}
        setMessages={setMessages}
        stop={stop}
        append={append}
      />
    </div>
  )
}
