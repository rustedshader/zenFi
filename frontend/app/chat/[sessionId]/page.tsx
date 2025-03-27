import { Chat } from '@/components/chat'

export default async function ChatSessionPage({
  params
}: {
  params: { sessionId: string }
}) {
  const sessionId = await Promise.resolve(params.sessionId)

  return <Chat id={sessionId} sessionId={sessionId} />
}
