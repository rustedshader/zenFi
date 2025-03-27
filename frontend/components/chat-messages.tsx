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
    <div className="px-2 sm:px-4 py-4 sm:py-6 max-w-4xl mx-auto">
      <div className="space-y-4 sm:space-y-6">
        {messages.map((message, index) => (
          <div
            key={message.id || `message-${index}`}
            className={`flex ${
              message.role === 'user' ? 'justify-end' : 'justify-start'
            }`}
          >
            <div
              className={`max-w-[90%] sm:max-w-[85%] rounded-2xl px-4 py-3 shadow-sm ${
                message.role === 'user'
                  ? 'bg-blue-500 text-white'
                  : 'bg-white dark:bg-gray-800 border border-gray-100 dark:border-gray-700'
              }`}
            >
              <div className="flex items-start gap-2">
                {message.role === 'assistant' && (
                  <div className="flex-shrink-0 mt-1">
                    <div className="size-6 rounded-full bg-gray-100 dark:bg-gray-700 flex items-center justify-center">
                      <svg
                        className="size-4 text-gray-600 dark:text-gray-300"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                        xmlns="http://www.w3.org/2000/svg"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"
                        />
                      </svg>
                    </div>
                  </div>
                )}
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
                  />
                  {message.sources && message.sources.length > 0 && (
                    <div className="mt-3 pt-2 border-t border-gray-200 dark:border-gray-700">
                      <span className="text-xs font-medium text-gray-500 dark:text-gray-400">
                        Sources:
                      </span>
                      <ul className="mt-1 space-y-1">
                        {message.sources.map((source, idx) => (
                          <li
                            key={idx}
                            className="text-xs text-gray-600 dark:text-gray-300"
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
          </div>
        ))}
      </div>
      {isLoading && (
        <div className="flex justify-start mt-4">
          <div className="bg-white dark:bg-gray-800 rounded-2xl px-4 py-3 shadow-sm border border-gray-100 dark:border-gray-700">
            <div className="flex items-start gap-2">
              <div className="flex-shrink-0 mt-1">
                <div className="size-6 rounded-full bg-gray-100 dark:bg-gray-700 flex items-center justify-center">
                  <svg
                    className="size-4 text-gray-600 dark:text-gray-300"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                    xmlns="http://www.w3.org/2000/svg"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"
                    />
                  </svg>
                </div>
              </div>
              <div className="flex-1">
                <Spinner />
              </div>
            </div>
          </div>
        </div>
      )}
      <div ref={messagesEndRef} />
    </div>
  )
}
