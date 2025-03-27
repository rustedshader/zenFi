import { Chat } from '@/components/chat'
import { notFound } from 'next/navigation'

async function getChat(sessionId: string, userId: string) {
  // Add your chat fetching logic here
  const response = await fetch(`/api/chat/${sessionId}?userId=${userId}`)
  return response.json()
}

export async function generateMetadata({
  params
}: {
  params: { sessionId: string }
}) {
  const chat = await getChat(params.sessionId, 'anonymous')
  return {
    title: chat?.title?.toString().slice(0, 50) || 'Chat Session'
  }
}

export default async function ChatSessionPage({
  params
}: {
  params: { sessionId: string }
}) {
  const { sessionId } = params
  const chat = await getChat(sessionId, 'anonymous')
  if (!chat) {
    notFound()
  }
  return (
    <Chat id={sessionId} sessionId={sessionId} savedMessages={chat.messages} />
  )
}
