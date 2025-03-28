// frontend/components/chat-messages.tsx
import { useEffect, useRef } from 'react'
import { RenderMessage } from './render-message'
import { Loader2 } from 'lucide-react'

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

  const lastMessage = messages[messages.length - 1]
  const showLoading = isLoading && lastMessage.role === 'user'

  return (
    <div className="px-1 sm:px-4 py-2 sm:py-6 max-w-4xl mx-auto">
      <div className="space-y-3 sm:space-y-6">
        {messages.map((message, index) => (
          <div
            key={message.id || `message-${index}`}
            className={`flex ${
              message.role === 'user' ? 'justify-end' : 'justify-start'
            }`}
          >
            <div
              className={`${
                message.role === 'user'
                  ? 'max-w-[95%] sm:max-w-[85%] rounded-2xl px-3 py-2 sm:px-4 sm:py-3 shadow-sm bg-gray-100 dark:bg-gray-800 text-gray-900 dark:text-gray-100'
                  : 'max-w-[95%] sm:max-w-[85%] text-gray-900 dark:text-gray-100'
              }`}
            >
              <div className="flex-1">
                <RenderMessage
                  message={{
                    ...message,
                    id: message.id || `message-${index}`
                  }}
                  messageId={message.id || `message-${index}`}
                  getIsOpen={() => true}
                  onOpenChange={() => {}}
                  onQuerySelect={onQuerySelect}
                  chatId={chatId}
                  isLoading={isLoading && index === messages.length - 1}
                />
                {message.sources && message.sources.length > 0 && (
                  <div className="mt-2 sm:mt-3 pt-2 border-t border-gray-200 dark:border-gray-700">
                    <span className="text-xs font-medium text-gray-500 dark:text-gray-400">
                      Sources:
                    </span>
                    <ul className="mt-1 space-y-1">
                      {message.sources.map((source, idx) => (
                        <li
                          key={idx}
                          className="text-xs text-gray-600 dark:text-gray-300 break-words"
                        >
                          {JSON.stringify(source)}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            </div>
          </div>
        ))}
        {showLoading && (
          <div className="flex justify-start">
            <div className="max-w-[95%] sm:max-w-[85%] text-gray-900 dark:text-gray-100">
              <div className="flex items-center gap-2 p-4">
                <Loader2 className="size-4 animate-spin text-gray-400" />
                <span className="text-gray-500">AI is thinking...</span>
              </div>
            </div>
          </div>
        )}
      </div>
      <div ref={messagesEndRef} />
    </div>
  )
}
