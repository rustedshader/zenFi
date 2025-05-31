'use client'

import { ArrowRight, Microscope, Square } from 'lucide-react'
import { useRouter } from 'next/navigation'
import { useEffect, useRef, useState } from 'react'
import { Textarea } from './ui/textarea'
import { Button } from './ui/button'
import { motion } from 'framer-motion'
import { toast } from 'sonner'
import { cn } from '@/lib/utils'

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

  const autoResize = () => {
    const textarea = inputRef.current
    if (textarea) {
      textarea.style.height = 'auto'
      textarea.style.height = `${textarea.scrollHeight}px`
    }
  }

  useEffect(() => {
    autoResize()
  }, [input])

  const deepResearchToggle = () => {
    const newIsDeepSearch = !currentisDeepSearch
    onDeepSearchChange(newIsDeepSearch)
    toast.dismiss() // Dismiss any existing toasts before showing a new one
    toast.info(
      newIsDeepSearch ? 'Deep Research enabled' : 'Deep Research disabled'
    )
    console.log('isDeepSearch:', newIsDeepSearch)
  }

  return (
    <div className="fixed bottom-0 left-0 w-full bg-gradient-to-t from-background to-transparent">
      <div className="mx-auto max-w-3xl px-4 pb-6">
        <motion.form
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3 }}
          onSubmit={handleSubmit}
          className="relative"
        >
          <div className="relative rounded-2xl border border-gray-200 shadow-lg transition-colors bg-background">
            <Textarea
              ref={inputRef}
              name="input"
              rows={1}
              placeholder="How can I help?"
              value={input}
              onChange={e => {
                handleInputChange(e)
                autoResize()
              }}
              onCompositionStart={() => setIsComposing(true)}
              onCompositionEnd={() => setIsComposing(false)}
              disabled={isLoading}
              className={cn(
                'w-full resize-none focus:outline-none py-4 px-6 pr-24 text-base',
                'rounded-2xl border-none focus:ring-2',
                'min-h-[48px] max-h-[200px] scrollbar-hide',
                isLoading && 'opacity-50 cursor-not-allowed'
              )}
              onKeyDown={e => {
                if (e.key === 'Enter' && !e.shiftKey && !isComposing) {
                  e.preventDefault()
                  const form = e.currentTarget.form
                  if (form) {
                    form.requestSubmit()
                  }
                }
              }}
              aria-label="Chat input"
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
                className={cn(
                  'flex items-center space-x-1 rounded-xl px-3 py-1.5',
                  currentisDeepSearch
                    ? 'bg-blue-900 text-blue-400'
                    : 'hover:bg-gray-800'
                )}
              >
                <Microscope className="h-4 w-4" />
                <span className="text-sm">Deep</span>
              </Button>
              <Button
                type="submit"
                disabled={isLoading || input.trim().length === 0}
                className={cn(
                  'rounded-xl p-2.5 transition-all duration-200 bg-gray-800 hover:bg-gray-700 text-white',
                  'disabled:opacity-50 disabled:cursor-not-allowed'
                )}
                aria-label="Submit chat query"
              >
                {isLoading ? (
                  <svg
                    className="animate-spin h-5 w-5"
                    viewBox="0 0 24 24"
                    aria-label="Loading"
                  >
                    <circle
                      className="opacity-25"
                      cx="12"
                      cy="12"
                      r="10"
                      stroke="currentColor"
                      strokeWidth="4"
                    />
                    <path
                      className="opacity-75"
                      fill="currentColor"
                      d="M4 12a8 8 0 018-8v8H4z"
                    />
                  </svg>
                ) : (
                  <ArrowRight className="h-5 w-5" />
                )}
              </Button>
            </div>
          </div>
          <p className="text-xs text-gray-500 mt-3 text-center">
            ZenFi may provide inaccurate information. Always verify critical
            data.
          </p>
        </motion.form>
      </div>
    </div>
  )
}
