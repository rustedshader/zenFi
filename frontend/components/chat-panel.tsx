'use client'

import { ArrowUp, Square } from 'lucide-react'
import { useRouter } from 'next/navigation'
import { useEffect, useRef, useState } from 'react'
import Textarea from 'react-textarea-autosize'
import { Button } from './ui/button'
import { motion } from 'framer-motion'

interface Message {
  id?: string
  role: 'user' | 'assistant'
  content: string
  sources?: Array<{
    title: string
    url: string
    description?: string
  }>
}

interface ChatPanelProps {
  input: string
  handleInputChange: (e: React.ChangeEvent<HTMLTextAreaElement>) => void
  handleSubmit: (e: React.FormEvent<HTMLFormElement>) => void
  isLoading: boolean
  messages: Message[]
  setMessages: (messages: Message[]) => void
  stop: () => void
  append: (message: Message) => void
}

export function ChatPanel({
  input,
  handleInputChange,
  handleSubmit,
  isLoading,
  messages,
  setMessages,
  stop,
  append
}: ChatPanelProps) {
  const inputRef = useRef<HTMLTextAreaElement>(null)
  const isFirstRender = useRef(true)
  const [isComposing, setIsComposing] = useState(false)

  return (
    <div className="fixed bottom-0 left-0 w-full">
      <div className="mx-auto max-w-3xl px-2 sm:px-4 pb-4 sm:pb-6">
        <motion.form
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          onSubmit={handleSubmit}
          className="relative"
        >
          <div className="relative rounded-2xl bg-white border border-gray-200 shadow-sm overflow-hidden">
            <Textarea
              ref={inputRef}
              name="input"
              rows={2}
              maxRows={6}
              placeholder="How can I help?"
              value={input}
              onChange={handleInputChange}
              onCompositionStart={() => setIsComposing(true)}
              onCompositionEnd={() => setIsComposing(false)}
              className="w-full resize-none bg-transparent text-gray-900 placeholder:text-gray-500 focus:outline-none py-3 sm:py-5 px-3 sm:px-5 pr-12 text-sm sm:text-base"
              onKeyDown={e => {
                if (e.key === 'Enter' && !e.shiftKey && !isComposing) {
                  e.preventDefault()
                  const form = e.currentTarget.form
                  if (form) {
                    form.requestSubmit()
                  }
                }
              }}
            />
            <div className="absolute right-1 sm:right-2 bottom-1 sm:bottom-2">
              <Button
                type="submit"
                disabled={isLoading || input.trim().length === 0}
                className="bg-transparent hover:bg-gray-100 text-gray-600 hover:text-gray-900 rounded-lg p-1.5 sm:p-2"
              >
                {isLoading ? (
                  <Square className="size-4 sm:size-5" />
                ) : (
                  <ArrowUp className="size-4 sm:size-5" />
                )}
              </Button>
            </div>
          </div>
        </motion.form>
      </div>
    </div>
  )
}
