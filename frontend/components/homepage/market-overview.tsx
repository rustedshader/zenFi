'use client'
import { Activity, ArrowUp, Globe, TrendingDown } from 'lucide-react'
import { Card, CardContent } from '../ui/card'
import { Skeleton } from '../ui/skeleton'
import { useEffect, useState } from 'react'
import { toast } from 'sonner'

interface MarketIndex {
  name: string
  value: number
  change: number
  changePercent: number
}

interface DashboardInfo {
  market_status: string
  important_stocks: {
    [key: string]: {
      last_price: string
      points_change: string
      percentage_change: string
    }
  }
  current_time_ist: string
}

export default function MarketOverview() {
  const [currentTime, setCurrentTime] = useState<string>('')
  const [marketIndices, setMarketIndices] = useState<MarketIndex[]>([])
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState<boolean>(true) // Add loading state

  const fetchMarketInfo = async () => {
    try {
      setLoading(true) // Set loading to true before fetching
      const infoResponse = await fetch('/api/dashboard/info')
      if (!infoResponse.ok) throw new Error('Failed to fetch market info')
      const infoData: DashboardInfo = await infoResponse.json()

      setCurrentTime(infoData.current_time_ist)

      const indices: MarketIndex[] = [
        {
          name: 'NIFTY 50',
          value: parseFloat(infoData.important_stocks['%5ENSEI'].last_price),
          change: parseFloat(
            infoData.important_stocks['%5ENSEI'].points_change
          ),
          changePercent: parseFloat(
            infoData.important_stocks['%5ENSEI'].percentage_change
          )
        },
        {
          name: 'SENSEX',
          value: parseFloat(infoData.important_stocks['%5EBSESN'].last_price),
          change: parseFloat(
            infoData.important_stocks['%5EBSESN'].points_change
          ),
          changePercent: parseFloat(
            infoData.important_stocks['%5EBSESN'].percentage_change
          )
        },
        {
          name: 'NIFTY BANK',
          value: parseFloat(infoData.important_stocks['%5ENSEBANK'].last_price),
          change: parseFloat(
            infoData.important_stocks['%5ENSEBANK'].points_change
          ),
          changePercent: parseFloat(
            infoData.important_stocks['%5ENSEBANK'].percentage_change
          )
        }
      ]
      setMarketIndices(indices)
    } catch (err) {
      setError('Failed to load market data. Please try again later.')
      toast.error('Failed to load market data')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchMarketInfo()
  }, [])

  return (
    <div>
      <div className="px-4 pt-2 pb-1 text-xs text-right max-w-7xl mx-auto">
        {currentTime &&
          `Last updated: ${new Date(currentTime).toLocaleString('en-IN')}`}
      </div>
      <section className="">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-xl font-semibold">Market Overview</h2>
            <div className="flex items-center gap-2 text-sm text-gray-600">
              <Globe className="h-4 w-4" />
              Indian Markets
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {loading
              ? // Render Skeleton placeholders while loading
                Array.from({ length: 3 }).map((_, index) => (
                  <Card
                    key={index}
                    className="transition-all duration-200 border shadow-md"
                  >
                    <CardContent className="p-6">
                      <div className="flex justify-between items-start">
                        <div className="flex-1">
                          <Skeleton className="h-4 w-24 mb-2" />
                          <Skeleton className="h-8 w-32" />
                        </div>
                        <Skeleton className="h-6 w-20 rounded-full" />
                      </div>
                      <div className="mt-3 flex items-center justify-between">
                        <Skeleton className="h-4 w-16" />
                        <Skeleton className="h-4 w-12" />
                      </div>
                    </CardContent>
                  </Card>
                ))
              : // Render market indices when loaded
                marketIndices.map(index => (
                  <Card
                    key={index.name}
                    className="transition-all duration-200 border shadow-md"
                  >
                    <CardContent className="p-6">
                      <div className="flex justify-between items-start">
                        <div className="flex-1">
                          <h3 className="font-semibold text-sm uppercase tracking-wide">
                            {index.name}
                          </h3>
                          <p className="text-3xl font-bold mt-2 ">
                            {index.value.toLocaleString('en-IN')}
                          </p>
                        </div>
                        <div
                          className={`flex items-center space-x-1 px-3 py-1 rounded-full text-sm font-medium ${
                            index.change >= 0
                              ? 'text-green-700 border'
                              : 'text-red-700 border'
                          }`}
                        >
                          {index.change >= 0 ? (
                            <ArrowUp className="h-3 w-3" />
                          ) : (
                            <TrendingDown className="h-3 w-3" />
                          )}
                          <span>
                            {index.changePercent >= 0 ? '+' : ''}
                            {index.changePercent.toFixed(2)}%
                          </span>
                        </div>
                      </div>
                      <div className="mt-3 flex items-center justify-between">
                        <p
                          className={`text-sm font-medium ${
                            index.change >= 0
                              ? 'text-green-600'
                              : 'text-red-600'
                          }`}
                        >
                          {index.change >= 0 ? '+' : ''}
                          {index.change.toFixed(2)} pts
                        </p>
                        <div className="flex items-center text-xs">
                          <Activity className="h-3 w-3 mr-1" />
                          Live
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                ))}
          </div>
        </div>
      </section>
    </div>
  )
}
