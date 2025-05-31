'use client'
import { ArrowRight, Microscope } from 'lucide-react'
import { Button } from '../ui/button'
import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { toast } from 'sonner'
import { Textarea } from '../ui/textarea'

export default function HomeSearch() {
  const router = useRouter()
  const [input, setInput] = useState('')
  const [isDeepResearch, setIsDeepResearch] = useState(false)

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    if (!input.trim()) return

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
      toast.error('Failed to create chat session')
      router.push('/')
    }
  }
  return (
    <div>
      <form onSubmit={handleSubmit} className="relative">
        <div className="relative  overflow-hidden  transition-colors">
          <Textarea
            name="input"
            rows={1}
            placeholder="Ask me anything about stocks, markets, or your portfolio..."
            value={input}
            onChange={e => setInput(e.target.value)}
            className="rounded-2xl w-full resize-none bg-transparent focus:outline-none py-4 px-6 pr-20 text-base border"
            onKeyDown={e => {
              if (e.key === 'Enter' && !e.shiftKey) {
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
              onClick={() => {
                const newIsDeepResearch = !isDeepResearch
                setIsDeepResearch(newIsDeepResearch)
                console.log('isDeepResearch:', newIsDeepResearch)
              }}
              variant={isDeepResearch ? 'secondary' : 'ghost'}
              size="icon"
              title="Toggle Deep Research"
              aria-label={
                isDeepResearch
                  ? 'Disable Deep Research'
                  : 'Enable Deep Research'
              }
              className="border roundex-2xl w-full px-2"
            >
              <Microscope
                className={isDeepResearch ? 'text-blue-600' : 'text-gray-500'}
              />
              DeepResearch
            </Button>
            <Button
              type="submit"
              disabled={input.trim().length === 0}
              className=" rounded-xl p-2.5 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200 shadow-lg"
            >
              <ArrowRight />
            </Button>
          </div>
        </div>
        <p className="text-xs text-gray-500 mt-2 text-center">
          ZenFi Can make mistakes
        </p>
      </form>
    </div>
  )
}
