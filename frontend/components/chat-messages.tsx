import { useEffect, useMemo, useRef, useState } from 'react'
import { RenderMessage } from './render-message'
import { ToolSection } from './tool-section'
import { Spinner } from './ui/spinner'

// Custom Message type to match your API
interface Message {
  id?: string
  role: 'user' | 'assistant'
  content: string
  sources?: any[]
}

// Define JSONValue to match the original type
type JSONValue =
  | string
  | number
  | boolean
  | null
  | { [key: string]: JSONValue }
  | JSONValue[]

interface ChatMessagesProps {
  messages: Message[]
  data?: JSONValue[] | undefined
  onQuerySelect: (query: string) => void
  isLoading: boolean
  chatId?: string
}

export function ChatMessages({
  messages,
  data,
  onQuerySelect,
  isLoading,
  chatId
}: ChatMessagesProps) {
  const [openStates, setOpenStates] = useState<Record<string, boolean>>({})
  const manualToolCallId = 'manual-tool-call'

  // Add ref for the messages container
  const messagesEndRef = useRef<HTMLDivElement>(null)

  // Scroll to bottom function
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'instant' })
  }

  // Scroll to bottom on mount and when messages change
  useEffect(() => {
    scrollToBottom()
  }, [messages])

  useEffect(() => {
    const lastMessage = messages[messages.length - 1]
    if (lastMessage?.role === 'user') {
      setOpenStates({ [manualToolCallId]: true })
    }
  }, [messages])

  // get last tool data for manual tool call
  const lastToolData = useMemo(() => {
    if (!data || !Array.isArray(data) || data.length === 0) return null
    const lastItem = data[data.length - 1] as {
      type: 'tool_call'
      data: {
        toolCallId: string
        state: 'call' | 'result'
        toolName: string
        args: string
      }
    }
    if (lastItem?.type !== 'tool_call') return null
    const toolData = lastItem.data
    return {
      state: 'call' as const,
      toolCallId: toolData.toolCallId,
      toolName: toolData.toolName,
      args: toolData.args ? JSON.parse(toolData.args) : undefined
    }
  }, [data])

  if (!messages.length) return null

  const lastUserIndex =
    messages.length -
    1 -
    [...messages].reverse().findIndex(msg => msg.role === 'user')

  const showLoading = isLoading && messages[messages.length - 1].role === 'user'

  const getIsOpen = (id: string) => {
    if (id.includes('call')) {
      return openStates[id] ?? true
    }
    const baseId = id.endsWith('-related') ? id.slice(0, -8) : id
    const index = messages.findIndex(msg => msg.id === baseId)
    return openStates[id] ?? index >= lastUserIndex
  }

  const handleOpenChange = (id: string, open: boolean) => {
    setOpenStates(prev => ({
      ...prev,
      [id]: open
    }))
  }

  return (
    <div className="relative mx-auto px-4 w-full">
      {messages.map((message, index) => (
        <div
          key={message.id || `message-${index}`}
          className="mb-4 flex flex-col gap-4"
        >
          <RenderMessage
            message={{
              ...message,
              id: message.id || `message-${index}` // Ensure an id exists
            }}
            messageId={message.id || `message-${index}`}
            getIsOpen={getIsOpen}
            onOpenChange={handleOpenChange}
            onQuerySelect={onQuerySelect}
            chatId={chatId}
          />
        </div>
      ))}
      {showLoading &&
        (lastToolData ? (
          <ToolSection
            key={manualToolCallId}
            tool={lastToolData}
            isOpen={getIsOpen(manualToolCallId)}
            onOpenChange={open => handleOpenChange(manualToolCallId, open)}
          />
        ) : (
          <Spinner />
        ))}
      <div ref={messagesEndRef} /> {/* Add empty div as scroll anchor */}
    </div>
  )
}
