'use client'
import { useCallback, useEffect, useState } from 'react'
import { toast } from 'sonner'
import { ChatMessages } from './chat-messages'
import { ChatPanel } from './chat-panel'

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

  // Send message via HTTP streaming
  const sendMessage = useCallback(async (messageContent: string) => {
    setIsLoading(true)

    const userMessage: Message = {
      role: 'user',
      content: messageContent,
      id: `user-${Date.now()}`
    }

    setMessages(prev => [...prev, userMessage])
    setInput('')

    try {
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_BACKEND_API_URL}/chat/stream_http`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({ message: messageContent })
        }
      )

      if (!response.ok) {
        throw new Error('Network response was not ok')
      }

      if (!response.body) {
        throw new Error('Response body is null')
      }

      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let done = false
      let assistantMessage: Message | null = null

      while (!done) {
        const { value, done: doneReading } = await reader.read()
        done = doneReading
        const chunk = decoder.decode(value, { stream: true })

        // Split the chunk into lines
        const lines = chunk.split('\n\n')
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6))

              // Check for finish reason
              if (data.finishReason) {
                if (data.finishReason === 'stop') {
                  setIsLoading(false)
                  break
                } else if (data.finishReason === 'error') {
                  toast.error(data.error || 'An error occurred')
                  setIsLoading(false)
                  break
                }
              }

              // Process content chunks
              if (data.content) {
                if (!assistantMessage) {
                  assistantMessage = {
                    role: 'assistant',
                    content: data.content,
                    id: `assistant-${Date.now()}`
                  }
                  setMessages(prev => [...prev, assistantMessage as Message])
                } else {
                  assistantMessage.content += data.content
                  setMessages(prev => [
                    ...prev.slice(0, -1),
                    assistantMessage as Message
                  ])
                }
              }
            } catch (parseError) {
              console.error('Error parsing streaming data:', parseError)
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
  }, [])

  // Handle form submission
  const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    if (input.trim()) {
      sendMessage(input.trim())
    }
  }

  // Handle input change
  const handleInputChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value)
  }

  // Handle query selection
  const onQuerySelect = (query: string) => {
    sendMessage(query)
  }

  // Handle initial query
  useEffect(() => {
    if (query) {
      sendMessage(query)
    }
  }, [query, sendMessage])

  return (
    <div className="flex flex-col w-full max-w-3xl pt-14 pb-60 mx-auto stretch">
      <ChatMessages
        messages={messages}
        onQuerySelect={onQuerySelect}
        isLoading={isLoading}
        chatId={id}
      />
      <ChatPanel
        input={input}
        handleInputChange={handleInputChange}
        handleSubmit={handleSubmit}
        isLoading={isLoading}
        messages={messages}
        setMessages={setMessages}
        stop={() => setIsLoading(false)}
        query={query}
        append={message => {
          setMessages(prev => [...prev, message])
          if (message.role === 'user') {
            sendMessage(message.content)
          }
        }}
      />
    </div>
  )
}
