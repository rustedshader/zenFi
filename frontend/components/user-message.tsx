import React from 'react'
import { CollapsibleMessage } from './collapsible-message'

interface UserMessageProps {
  message: string
}

export const UserMessage: React.FC<UserMessageProps> = ({ message }) => {
  return (
    <CollapsibleMessage role="user">
      <div className="bg-blue-500 text-white p-3 rounded-lg inline-block max-w-full">
        {message}
      </div>
    </CollapsibleMessage>
  )
}
