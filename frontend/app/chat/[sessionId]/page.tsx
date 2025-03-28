import { Chat } from '@/components/chat'

export default async function ChatSessionPage({
  params,
  searchParams
}: {
  params: Promise<{ sessionId: string }>
  searchParams: Promise<{ query?: string }>
}) {
  const { sessionId } = await params
  const { query } = await searchParams

  return <Chat id={sessionId} sessionId={sessionId} initialQuery={query} />
}
