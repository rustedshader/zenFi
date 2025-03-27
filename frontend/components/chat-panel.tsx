'use client'

import { ArrowUp, MessageCirclePlus, Square } from 'lucide-react'
import { useRouter } from 'next/navigation'
import { useEffect, useRef, useState } from 'react'
import Textarea from 'react-textarea-autosize'
import { Button } from './ui/button'
import { IconLogo } from './ui/icons'
import { toast } from 'sonner'

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
  query?: string
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
  query,
  stop,
  append
}: ChatPanelProps) {
  const [showEmptyScreen, setShowEmptyScreen] = useState(false)
  const router = useRouter()
  const inputRef = useRef<HTMLTextAreaElement>(null)
  const isFirstRender = useRef(true)
  const [isComposing, setIsComposing] = useState(false)
  const [enterDisabled, setEnterDisabled] = useState(false)

  const handleCompositionStart = () => setIsComposing(true)
  const handleCompositionEnd = () => {
    setIsComposing(false)
    setEnterDisabled(true)
    setTimeout(() => {
      setEnterDisabled(false)
    }, 300)
  }

  const handleNewChat = async () => {
    try {
      const response = await fetch('/api/sessions', { method: 'POST' })
      if (response.ok) {
        const data = await response.json()
        setMessages([])
        router.push(`/chat/${data.session_id}`)
      } else {
        toast.error('Failed to create new session')
      }
    } catch (error) {
      toast.error('Error creating new session')
    }
  }

  useEffect(() => {
    if (isFirstRender.current && query && query.trim().length > 0) {
      append({
        role: 'user',
        content: query,
        id: `user-message-${Date.now()}`
      })
      isFirstRender.current = false
    }
  }, [query, append])

  return (
    <div className="fixed bottom-0 sm:bottom-4 left-0 sm:left-1/2 sm:-translate-x-1/2 w-full sm:w-full sm:max-w-4xl px-2 sm:px-4">
      {messages.length === 0 ? (
        <div className="flex flex-col items-center justify-center min-h-[60vh]">
          <div className="mb-8">
            <IconLogo className="size-12 sm:size-16 text-muted-foreground" />
          </div>
          <form onSubmit={handleSubmit} className="w-full max-w-2xl">
            <div className="relative flex flex-col w-full gap-2 bg-white dark:bg-gray-800 rounded-t-2xl sm:rounded-2xl border border-gray-200 dark:border-gray-700 shadow-lg">
              <Textarea
                ref={inputRef}
                name="input"
                rows={2}
                maxRows={5}
                tabIndex={0}
                onCompositionStart={handleCompositionStart}
                onCompositionEnd={handleCompositionEnd}
                placeholder="Ask a question..."
                spellCheck={false}
                value={input}
                className="resize-none w-full min-h-[60px] bg-transparent border-0 px-4 py-3 text-base placeholder:text-gray-500 dark:placeholder:text-gray-400 focus-visible:outline-none"
                onChange={e => {
                  handleInputChange(e)
                  setShowEmptyScreen(e.target.value.length === 0)
                }}
                onKeyDown={e => {
                  if (
                    e.key === 'Enter' &&
                    !e.shiftKey &&
                    !isComposing &&
                    !enterDisabled
                  ) {
                    if (input.trim().length === 0) {
                      e.preventDefault()
                      return
                    }
                    e.preventDefault()
                    const textarea = e.target as HTMLTextAreaElement
                    textarea.form?.requestSubmit()
                  }
                }}
                onFocus={() => setShowEmptyScreen(true)}
                onBlur={() => setShowEmptyScreen(false)}
              />
              <div className="flex items-center justify-end p-2 sm:p-3">
                <Button
                  type={isLoading ? 'button' : 'submit'}
                  size="icon"
                  variant="outline"
                  disabled={input.length === 0 && !isLoading}
                  onClick={isLoading ? stop : undefined}
                  className="size-8 sm:size-10"
                >
                  {isLoading ? (
                    <Square size={16} className="sm:size-20" />
                  ) : (
                    <ArrowUp size={16} className="sm:size-20" />
                  )}
                </Button>
              </div>
            </div>
          </form>
        </div>
      ) : (
        <form onSubmit={handleSubmit} className="w-full">
          <div className="relative flex flex-col w-full gap-2 bg-white dark:bg-gray-800 rounded-t-2xl sm:rounded-2xl border border-gray-200 dark:border-gray-700 shadow-lg">
            <Textarea
              ref={inputRef}
              name="input"
              rows={2}
              maxRows={5}
              tabIndex={0}
              onCompositionStart={handleCompositionStart}
              onCompositionEnd={handleCompositionEnd}
              placeholder="Ask a question..."
              spellCheck={false}
              value={input}
              className="resize-none w-full min-h-[60px] bg-transparent border-0 px-4 py-3 text-base placeholder:text-gray-500 dark:placeholder:text-gray-400 focus-visible:outline-none"
              onChange={e => {
                handleInputChange(e)
              }}
              onKeyDown={e => {
                if (
                  e.key === 'Enter' &&
                  !e.shiftKey &&
                  !isComposing &&
                  !enterDisabled
                ) {
                  if (input.trim().length === 0) {
                    e.preventDefault()
                    return
                  }
                  e.preventDefault()
                  const textarea = e.target as HTMLTextAreaElement
                  textarea.form?.requestSubmit()
                }
              }}
            />
            <div className="flex items-center justify-between p-2 sm:p-3">
              <div className="flex items-center gap-2">
                {messages.length > 0 && (
                  <Button
                    variant="outline"
                    size="icon"
                    onClick={handleNewChat}
                    type="button"
                    disabled={isLoading}
                    className="size-8 sm:size-10"
                  >
                    <MessageCirclePlus className="size-4 sm:size-5" />
                  </Button>
                )}
              </div>
              <div className="flex items-center gap-2">
                <Button
                  type={isLoading ? 'button' : 'submit'}
                  size="icon"
                  variant="outline"
                  disabled={input.length === 0 && !isLoading}
                  onClick={isLoading ? stop : undefined}
                  className="size-8 sm:size-10"
                >
                  {isLoading ? (
                    <Square size={16} className="sm:size-20" />
                  ) : (
                    <ArrowUp size={16} className="sm:size-20" />
                  )}
                </Button>
              </div>
            </div>
          </div>
        </form>
      )}
    </div>
  )
}
