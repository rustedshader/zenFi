// frontend/components/chat-messages.tsx
import { useEffect, useRef } from 'react'
import { RenderMessage } from './render-message'
import { Spinner } from './ui/spinner'

interface Message {
  id?: string
  role: 'user' | 'assistant'
  content: string
  sources?: any[]
}

interface ChatMessagesProps {
  messages: Message[]
  data?: any
  onQuerySelect: (query: string) => void
  isLoading: boolean
  chatId?: string
}

export function ChatMessages({
  messages,
  onQuerySelect,
  isLoading,
  chatId
}: ChatMessagesProps) {
  const messagesEndRef = useRef<HTMLDivElement>(null)

  // Scroll to the bottom whenever messages update
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  if (!messages.length) return null

  return (
    <div className="px-4 py-4">
      {messages.map((message, index) => (
        <div
          key={message.id || `message-${index}`}
          className="mb-4 flex flex-col gap-4"
        >
          <RenderMessage
            message={{ ...message, id: message.id || `message-${index}` }}
            messageId={message.id || `message-${index}`}
            getIsOpen={() => true}
            onOpenChange={() => {}}
            onQuerySelect={onQuerySelect}
            chatId={chatId}
          />
          {message.sources && message.sources.length > 0 && (
            <div className="mt-2 text-sm">
              <span>Sources:</span>
              <ul className="list-disc pl-4">
                {message.sources.map((source, idx) => (
                  <li key={idx}>{JSON.stringify(source)}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      ))}
      {isLoading && <Spinner />}
      <div ref={messagesEndRef} />
    </div>
  )
}
