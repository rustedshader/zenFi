import { Chat } from '@/components/chat'

export default async function ChatSessionPage({
  params,
  searchParams
}: {
  params: Promise<{ sessionId: string }>
  searchParams: { query?: string }
}) {
  const { sessionId } = await params
  const query = searchParams.query

  return <Chat id={sessionId} sessionId={sessionId} query={query} />
}
