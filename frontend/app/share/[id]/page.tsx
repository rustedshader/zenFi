import { Chat } from '@/components/chat'
import { getSharedChat } from '@/lib/actions/chat'
import { convertToUIMessages } from '@/lib/utils'
import { notFound } from 'next/navigation'

// Define your custom Message interface to match Chat component expectations
interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  sources?: any[]
}

export async function generateMetadata({
  params
}: {
  params: Promise<{ id: string }>
}) {
  const { id } = await params
  const chat = await getSharedChat(id)

  if (!chat || !chat.sharePath) {
    return notFound()
  }

  return {
    title: chat?.title.toString().slice(0, 50) || 'Search'
  }
}

export default async function SharePage({
  params
}: {
  params: Promise<{ id: string }>
}) {
  const { id } = await params
  const chat = await getSharedChat(id)

  if (!chat || !chat.sharePath) {
    return notFound()
  }

  // Convert AI SDK messages to your custom Message type
  const messages: Message[] = convertToUIMessages(chat.messages)
    .filter(
      (msg): msg is Message =>
        (msg.role === 'user' || msg.role === 'assistant') &&
        typeof msg.id === 'string'
    )
    .map((msg: Message) => ({
      id: msg.id,
      role: msg.role as 'user' | 'assistant', // Type assertion since we filtered above
      content: msg.content,
      sources: msg.sources
    }))

  return <Chat id={chat.id} savedMessages={messages} />
}
