'use client'

import { ArrowRight, Microscope, Square } from 'lucide-react'
import { useRouter } from 'next/navigation'
import { useEffect, useRef, useState } from 'react'
import { Textarea } from './ui/textarea'
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
  currentisDeepSearch: boolean
  onDeepSearchChange: (newToolType: boolean) => void
}

export function ChatPanel({
  input,
  handleInputChange,
  handleSubmit,
  isLoading,
  messages,
  setMessages,
  stop,
  append,
  currentisDeepSearch,
  onDeepSearchChange
}: ChatPanelProps) {
  const inputRef = useRef<HTMLTextAreaElement>(null)
  const [isComposing, setIsComposing] = useState(false)

  const deepResearchToggle = () => {
    const newIsDeepSearch = !currentisDeepSearch
    onDeepSearchChange(newIsDeepSearch)
    console.log('isDeepSearch:', newIsDeepSearch)
  }

  return (
    <div className="fixed bottom-0 left-0 w-full">
      <div className="mx-auto max-w-3xl px-2 sm:px-4 pb-4 sm:pb-6">
        <motion.form
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          onSubmit={handleSubmit}
          className="relative"
        >
          <div className="relative rounded-2xl border border-gray-200 shadow-lg overflow-hidden transition-colors">
            <Textarea
              ref={inputRef}
              name="input"
              rows={1}
              placeholder="How can I help?"
              value={input}
              onChange={handleInputChange}
              onCompositionStart={() => setIsComposing(true)}
              onCompositionEnd={() => setIsComposing(false)}
              disabled={isLoading}
              className="w-full resize-none focus:outline-none py-4 px-6 pr-20 text-base disabled:opacity-50 disabled:cursor-not-allowed"
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
            <div className="absolute right-3 bottom-3 flex items-center space-x-2">
              <Button
                type="button"
                disabled={isLoading}
                onClick={deepResearchToggle}
                variant={currentisDeepSearch ? 'secondary' : 'ghost'}
                size="sm"
                title="Toggle Deep Research"
                aria-label={
                  currentisDeepSearch
                    ? 'Disable Deep Research'
                    : 'Enable Deep Research'
                }
                className="border rounded-xl px-2 flex items-center space-x-1"
              >
                <Microscope
                  className={
                    currentisDeepSearch ? 'text-blue-600' : 'text-gray-500'
                  }
                />
                <span className="text-sm">DeepResearch</span>
              </Button>
              <Button
                type="submit"
                disabled={isLoading || input.trim().length === 0}
                className="rounded-xl p-2.5 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200 shadow-lg"
              >
                {isLoading ? (
                  <Square className="size-5" />
                ) : (
                  <ArrowRight className="size-5" />
                )}
              </Button>
            </div>
          </div>
          <p className="text-xs mt-2 text-center">ZenFi can make mistakes</p>
        </motion.form>
      </div>
    </div>
  )
}
