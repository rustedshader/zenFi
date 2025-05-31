'use client'
import { ArrowRight, Microscope } from 'lucide-react'
import { Button } from '../ui/button'
import { useState, useRef } from 'react'
import { useRouter } from 'next/navigation'
import { toast } from 'sonner'
import { Textarea } from '../ui/textarea'
import { cn } from '@/lib/utils'

export default function HomeSearch() {
  const router = useRouter()
  const [input, setInput] = useState('')
  const [isDeepResearch, setIsDeepResearch] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    if (!input.trim()) return

    setIsLoading(true)
    try {
      const response = await fetch('/api/sessions/init', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: input.trim(), isDeepResearch })
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.error || 'Failed to create session')
      }

      const data = await response.json()
      router.push(
        `/chat/${data.session_id}?query=${encodeURIComponent(
          input.trim()
        )}&isDeepResearch=${isDeepResearch}`
      )
    } catch (error) {
      console.error('Error:', error)
      toast.error('Failed to create chat session. Please try again.')
      router.push('/')
    } finally {
      setIsLoading(false)
    }
  }

  // Auto-resize textarea
  const autoResize = () => {
    const textarea = textareaRef.current
    if (textarea) {
      textarea.style.height = 'auto'
      textarea.style.height = `${textarea.scrollHeight}px`
    }
  }

  return (
    <div className="w-full max-w-2xl mx-auto px-4">
      <form onSubmit={handleSubmit} className="relative">
        <div className="relative rounded-2xl  border transition-colors">
          <Textarea
            ref={textareaRef}
            name="input"
            rows={1}
            placeholder="Ask me anything about stocks, markets, or your portfolio..."
            value={input}
            onChange={e => {
              setInput(e.target.value)
              autoResize()
            }}
            className={cn(
              'w-full resize-none  focus:outline-none py-4 px-6 pr-24 text-base',
              'rounded-2xl border-none focus:ring-2',
              'min-h-[48px] max-h-[200px] scrollbar-hide'
            )}
            onKeyDown={e => {
              if (e.key === 'Enter' && !e.shiftKey) {
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
              onClick={() => {
                const newIsDeepResearch = !isDeepResearch
                setIsDeepResearch(newIsDeepResearch)
                toast.info(
                  newIsDeepResearch
                    ? 'Deep Research enabled'
                    : 'Deep Research disabled'
                )
              }}
              variant={isDeepResearch ? 'secondary' : 'ghost'}
              size="sm"
              title="Toggle Deep Research"
              aria-label={
                isDeepResearch
                  ? 'Disable Deep Research'
                  : 'Enable Deep Research'
              }
              className={cn(
                'flex items-center space-x-1 rounded-xl px-3 py-1.5',
                isDeepResearch
                  ? 'bg-blue-900 text-blue-400'
                  : 'hover:bg-gray-800'
              )}
            >
              <Microscope className="h-4 w-4" />
              <span className="text-sm">Deep</span>
            </Button>
            <Button
              type="submit"
              disabled={input.trim().length === 0 || isLoading}
              className={cn(
                'rounded-xl p-2.5 transition-all duration-200 bg-gray-800 hover:bg-gray-700 text-white',
                'disabled:opacity-50 disabled:cursor-not-allowed'
              )}
              aria-label="Submit chat query"
            >
              {isLoading ? (
                <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
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
          ZenFi may provide inaccurate information. Always verify critical data.
        </p>
      </form>
    </div>
  )
}
