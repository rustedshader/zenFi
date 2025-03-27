import React from 'react'
import { CollapsibleMessage } from './collapsible-message'

interface UserMessageProps {
  message: string
}

export function UserMessage({ message }: UserMessageProps) {
  return (
    <div className="prose dark:prose-invert max-w-none">
      <p className="text-base leading-relaxed whitespace-pre-wrap">{message}</p>
    </div>
  )
}
