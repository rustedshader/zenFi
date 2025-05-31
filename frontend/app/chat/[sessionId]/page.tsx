import { Chat } from '@/components/chat'

export default async function ChatSessionPage({
  params,
  searchParams
}: {
  params: Promise<{ sessionId: string }>
  searchParams: Promise<{ query?: string; isDeepResearch?: string }>
}) {
  const { sessionId } = await params
  const { query, isDeepResearch } = await searchParams
  const isDeepResearchBool = isDeepResearch === 'true'

  return (
    <Chat
      id={sessionId}
      sessionId={sessionId}
      initialQuery={query}
      isDeepResearch={isDeepResearchBool}
    />
  )
}
