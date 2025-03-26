import { Chat } from '@/components/chat'
import { getChat } from '@/lib/actions/chat'
import { convertToUIMessages } from '@/lib/utils'
import { notFound, redirect } from 'next/navigation'

// Your custom Message type (should match what's used in Chat component)
interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  sources?: any[]
}

export const maxDuration = 60

export async function generateMetadata({
  params
}: {
  params: Promise<{ id: string }>
}) {
  const { id } = await params
  const chat = await getChat(id, 'anonymous')
  return {
    title: chat?.title.toString().slice(0, 50) ?? 'Search'
  }
}

export default async function SearchPage({
  params
}: {
  params: Promise<{ id: string }>
}) {
  const userId = 'anonymous'
  const { id } = await params

  const chat = await getChat(id, userId)
  if (!chat) {
    redirect('/')
  }

  if (chat.userId !== userId) {
    notFound()
  }

  // Convert AI SDK messages to your custom Message type
  const messages: Message[] = convertToUIMessages(chat.messages ?? [])
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

  return <Chat id={id} savedMessages={messages} />
}
