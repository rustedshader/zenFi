'use client'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { useAuth } from '@/contexts/auth-context'
import { useState } from 'react'
import MarketOverview from '@/components/homepage/market-overview'
import PinnedStocks from '@/components/homepage/pinned-stocks'
import HomeSearch from '@/components/homepage/home-search'
import Image from 'next/image'
import ZenfiLogo from '@/public/zenfi_logo.png'

export default function Page() {
  const [error, setError] = useState<string | null>(null)
  const { isLoading: isAuthLoading } = useAuth()

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
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 items-stretch">
          <div className="lg:col-span-1 flex flex-col space-y-6">
            <div className="flex-1">
              <PinnedStocks />
            </div>
          </div>
          <div className="lg:col-span-2 flex flex-col">
            <Card className="shadow-md border flex-1">
              <CardContent className="p-8 flex flex-col items-center">
                <div className="text-center mb-6">
                  <div className="flex items-center justify-center mb-3 space-x-3">
                    <Image
                      src={ZenfiLogo}
                      alt="zenfi_logo"
                      height={40}
                      width={40}
                      priority
                      className="block"
                    />
                    <h1 className="text-4xl font-bold">ZenFi AI</h1>
                  </div>
                  <p className="text-xl opacity-50 mb-6 max-w-2xl mx-auto">
                    Your intelligent finance assistant for smarter investment
                    decisions
                  </p>
                </div>
                <div className="w-full">
                  <HomeSearch />
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </div>
  )
}
