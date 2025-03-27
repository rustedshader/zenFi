'use client'

import { ArrowUp, MessageCirclePlus, Square } from 'lucide-react'
import { useRouter } from 'next/navigation'
import { useEffect, useRef, useState } from 'react'
import Textarea from 'react-textarea-autosize'
import { EmptyScreen } from './empty-screen'
import { SearchModeToggle } from './search-mode-toggle'
import { Button } from './ui/button'
import { IconLogo } from './ui/icons'
import { toast } from 'sonner'

interface Message {
  id?: string
  role: 'user' | 'assistant'
  content: string
  sources?: any[]
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

  // New Chat button now creates a new session and routes to /chat/[sessionId]
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

  // Automatically submit query on first render if provided
  useEffect(() => {
    if (isFirstRender.current && query && query.trim().length > 0) {
      append({
        role: 'user',
        content: query,
        id: `user-message-${Date.now()}`
      })
      isFirstRender.current = false
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [query])

  return (
    <div className="mx-auto w-full bg-white dark:bg-gray-900 p-4">
      {messages.length === 0 ? (
        <div className="flex flex-col items-center justify-center">
          <div className="mb-8">
            <IconLogo className="size-12 text-muted-foreground" />
          </div>
          <form onSubmit={handleSubmit} className="max-w-3xl w-full px-6">
            <div className="relative flex flex-col w-full gap-2 bg-gray-100 dark:bg-gray-800 rounded-3xl border border-gray-300 dark:border-gray-700">
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
                className="resize-none w-full min-h-12 bg-transparent border-0 px-4 py-3 text-sm placeholder:text-gray-500 dark:placeholder:text-gray-400 focus-visible:outline-none"
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
              <div className="flex items-center justify-between p-3">
                <div className="flex items-center gap-2">
                  <SearchModeToggle />
                </div>
                <div className="flex items-center gap-2">
                  {messages.length > 0 && (
                    <Button
                      variant="outline"
                      size="icon"
                      onClick={handleNewChat}
                      type="button"
                      disabled={isLoading}
                    >
                      <MessageCirclePlus className="size-4" />
                    </Button>
                  )}
                  <Button
                    type={isLoading ? 'button' : 'submit'}
                    size="icon"
                    variant="outline"
                    disabled={input.length === 0 && !isLoading}
                    onClick={isLoading ? stop : undefined}
                  >
                    {isLoading ? <Square size={20} /> : <ArrowUp size={20} />}
                  </Button>
                </div>
              </div>
            </div>
          </form>
        </div>
      ) : (
        <form
          onSubmit={handleSubmit}
          className="max-w-3xl w-full mx-auto px-2 py-4"
        >
          <div className="relative flex flex-col w-full gap-2 bg-gray-100 dark:bg-gray-800 rounded-3xl border border-gray-300 dark:border-gray-700">
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
              className="resize-none w-full min-h-12 bg-transparent border-0 px-4 py-3 text-sm placeholder:text-gray-500 dark:placeholder:text-gray-400 focus-visible:outline-none"
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
            <div className="flex items-center justify-between p-3">
              <div className="flex items-center gap-2">
                <SearchModeToggle />
              </div>
              <div className="flex items-center gap-2">
                {messages.length > 0 && (
                  <Button
                    variant="outline"
                    size="icon"
                    onClick={handleNewChat}
                    type="button"
                    disabled={isLoading}
                  >
                    <MessageCirclePlus className="size-4" />
                  </Button>
                )}
                <Button
                  type={isLoading ? 'button' : 'submit'}
                  size="icon"
                  variant="outline"
                  disabled={input.length === 0 && !isLoading}
                  onClick={isLoading ? stop : undefined}
                >
                  {isLoading ? <Square size={20} /> : <ArrowUp size={20} />}
                </Button>
              </div>
            </div>
          </div>
        </form>
      )}
    </div>
  )
}
