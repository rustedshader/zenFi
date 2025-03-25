import { AnswerSection } from './answer-section'
import { UserMessage } from './user-message'

// Custom Message type to match your API
interface Message {
  id?: string
  role: 'user' | 'assistant'
  content: string
  sources?: any[]
}

interface RenderMessageProps {
  message: Message
  messageId: string
  getIsOpen: (id: string) => boolean
  onOpenChange: (id: string, open: boolean) => void
  onQuerySelect: (query: string) => void
  chatId?: string
}

export function RenderMessage({
  message,
  messageId,
  getIsOpen,
  onOpenChange,
  onQuerySelect,
  chatId
}: RenderMessageProps) {
  if (message.role === 'user') {
    return <UserMessage message={message.content} />
  }

  return (
    <AnswerSection
      key={messageId}
      content={message.content}
      isOpen={getIsOpen(messageId)}
      onOpenChange={open => onOpenChange(messageId, open)}
      chatId={chatId}
      sources={message.sources}
    />
  )
}
