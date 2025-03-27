'use client'
import { Chat } from '@/components/chat'
import { useParams } from 'next/navigation'

export default function ChatSessionPage() {
  const params = useParams()
  const sessionId = params.sessionId as string
  return <Chat id={sessionId} sessionId={sessionId} />
}
