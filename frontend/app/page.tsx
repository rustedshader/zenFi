'use client'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { useAuth } from '@/contexts/auth-context'
import { useRouter } from 'next/navigation'
import { useEffect, useState, useCallback } from 'react' // Added useCallback
// import Textarea from 'react-textarea-autosize'
import { toast } from 'sonner'
import {
  TrendingUp,
  Star,
  BarChart3,
  Activity,
  Globe,
  Sparkles,
  Microscope,
  ArrowRight
} from 'lucide-react'
import MarketOverview from '@/components/homepage/market-overview'
import PinnedStocks from '@/components/homepage/pinned-stocks'
import { Textarea } from '@/components/ui/textarea'
import HomeSearch from '@/components/homepage/home-search'

export default function Page() {
  const router = useRouter()
  const [error, setError] = useState<string | null>(null)
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const { isLoggedIn, isLoading: isAuthLoading } = useAuth()
  const [isDeepResearch, setIsDeepResearch] = useState(false)

  useEffect(() => {
    if (!isAuthLoading && !isLoggedIn) {
      router.push('/login')
    }
  }, [router, isLoggedIn, isAuthLoading])

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
      setError('Failed to initialize chat. Please try again later.')
      toast.error('Failed to create chat session')
      router.push('/')
    } finally {
      setIsLoading(false)
    }
  }

  if (isAuthLoading) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center p-24">
        <div className="w-full max-w-md space-y-8">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
            <h1 className="text-2xl font-bold mt-4">Loading...</h1>
            <p className="mt-2 text-gray-600">
              Please wait while we load your dashboard.
            </p>
          </div>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center p-24">
        <div className="w-full max-w-md space-y-8">
          <div className="text-center">
            <h1 className="text-2xl font-bold text-red-600">Error</h1>
            <p className="mt-2 text-gray-600">{error}</p>
            <Button
              onClick={() => setError(null)}
              className="mt-4"
              variant="outline"
            >
              Try Again
            </Button>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="flex min-h-screen flex-col pb-32">
      <MarketOverview />
      <div className="flex-1 max-w-7xl mx-auto w-full px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          <div className="lg:col-span-1 space-y-6">
            <PinnedStocks />
          </div>
          <div className="lg:col-span-2">
            <Card className="shadow-md border h-fit">
              <CardContent className="p-8">
                <div className="text-center mb-8">
                  <div className="inline-flex items-center justify-center w-20 h-20 rounded-2xl mb-6 shadow-lg">
                    <Sparkles className="h-10 w-10 drop-shadow" />
                  </div>
                  <h1 className="text-4xl font-bold mb-3">
                    Welcome to ZenFi AI
                  </h1>
                  <p className="text-xl opacity-50 mb-8 max-w-2xl mx-auto">
                    Your intelligent finance assistant for smarter investment
                    decisions
                  </p>
                </div>
                <HomeSearch />
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </div>
  )
}
