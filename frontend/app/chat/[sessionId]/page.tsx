import { Chat } from '@/components/chat'

export default async function ChatSessionPage({
  params,
  searchParams
}: {
  params: { sessionId: string }
  searchParams: { query?: string }
}) {
  const { sessionId } = await params
  const { query } = searchParams

  return <Chat id={sessionId} sessionId={sessionId} initialQuery={query} />
}
