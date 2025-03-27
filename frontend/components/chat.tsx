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
    async (userMessage: Message) => {
      if (!sessionId) {
        toast.error('No active session')
        return
      }

      setIsLoading(true)
      // Append the user message to the chat
      setMessages(prev => [...prev, userMessage])
      setInput('')

      try {
        const response = await fetch('/api/chat', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ message: userMessage.content, sessionId })
        })

        if (!response.ok) throw new Error('Network response was not ok')

        const reader = response.body?.getReader()
        if (reader) {
          const decoder = new TextDecoder()
          let assistantMessage: Message = {
            role: 'assistant',
            content: '',
            id: `assistant-${Date.now()}`
          }
          setMessages(prev => [...prev, assistantMessage])

          let buffer = ''
          while (true) {
            const { done, value } = await reader.read()
            if (done) break

            // Accumulate stream chunks in a buffer
            buffer += decoder.decode(value, { stream: true })
            // Split the buffer on newlines
            const lines = buffer.split('\n')
            // Save any incomplete line back to the buffer
            buffer = lines.pop() || ''

            // Process complete lines
            for (const line of lines) {
              if (line.trim().startsWith('data:')) {
                const jsonStr = line.replace(/^data:\s*/, '')
                try {
                  const parsed = JSON.parse(jsonStr)
                  // Only update if there's a content field
                  if (parsed.content) {
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
        setIsLoading(false)
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
    <div className="flex flex-col h-[calc(100vh-8rem)]">
      {/* Chat messages area becomes scrollable */}
      <div className="flex-1 overflow-y-auto">
        <ChatMessages
          messages={messages}
          isLoading={isLoading}
          chatId={id}
          onQuerySelect={() => {}}
        />
      </div>
      {/* Chat input panel */}
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
