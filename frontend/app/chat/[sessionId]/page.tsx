import { Chat } from '@/components/chat'

export default async function ChatSessionPage({
  params
}: {
  params: Promise<{ sessionId: string }>
}) {
  const { sessionId } = await params

  return <Chat id={sessionId} sessionId={sessionId} />
}
