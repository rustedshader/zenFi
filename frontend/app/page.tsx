'use client'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { useAuth } from '@/contexts/auth-context'
import { useRouter } from 'next/navigation'
import { useEffect, useState, useCallback } from 'react' // Added useCallback
import Textarea from 'react-textarea-autosize'
import { toast } from 'sonner'
import {
  TrendingUp,
  TrendingDown,
  Search,
  Star,
  Plus,
  BarChart3,
  DollarSign,
  Activity,
  Globe,
  Clock,
  Users,
  ArrowUp,
  Sparkles
} from 'lucide-react'
import AddStockOverlay from '@/components/add-stock-overlay'

interface Stock {
  symbol: string
  name: string
  price: number
  change: number
  changePercent: number
}

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

interface StockData {
  symbol: string
  fast_info: {
    currency: string
    lastPrice: number
    previousClose: number
  }
  stock_points_change: string
  stocks_percentage_change: string
}

export default function Page() {
  const router = useRouter()
  const [error, setError] = useState<string | null>(null)
  const [input, setInput] = useState('')
  const [stockSearch, setStockSearch] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [isOverlayOpen, setIsOverlayOpen] = useState(false)
  const { isLoggedIn, isLoading: isAuthLoading } = useAuth()
  const [pinnedStocks, setPinnedStocks] = useState<Stock[]>([])
  const [marketIndices, setMarketIndices] = useState<MarketIndex[]>([])
  const [isDataLoading, setIsDataLoading] = useState(true)
  const [marketStatus, setMarketStatus] = useState<string>('')
  const [currentTime, setCurrentTime] = useState<string>('')

  // Get market status display info
  const getMarketStatusInfo = (status: string) => {
    const isLive =
      status.toLowerCase().includes('open') ||
      status.toLowerCase().includes('live')
    return {
      isLive,
      text: isLive ? 'Market Open' : 'Market Closed',
      color: isLive ? 'text-green-600 bg-green-50' : 'text-red-600 bg-red-50',
      icon: isLive ? Activity : Clock
    }
  }

  // Function to fetch pinned stocks
  const fetchPinnedStocks = useCallback(async () => {
    try {
      const stocksResponse = await fetch('/api/dashboard/stocks')
      if (!stocksResponse.ok) throw new Error('Failed to fetch stocks')
      const stocksData: { stocks: StockData[] } = await stocksResponse.json()

      const stocks: Stock[] = stocksData.stocks.map(stock => ({
        symbol: stock.symbol,
        name: stock.symbol, // You may need to map this to a proper name
        price: stock.fast_info.lastPrice,
        change: parseFloat(stock.stock_points_change),
        changePercent: parseFloat(stock.stocks_percentage_change)
      }))
      setPinnedStocks(stocks)
    } catch (err) {
      console.error('Failed to fetch pinned stocks:', err)
      toast.error('Failed to update pinned stocks')
    }
  }, []) // useCallback ensures this function has a stable identity

  useEffect(() => {
    if (!isAuthLoading && !isLoggedIn) {
      router.push('/login')
    }
  }, [router, isLoggedIn, isAuthLoading])

  useEffect(() => {
    const fetchDashboardData = async () => {
      setIsDataLoading(true)
      try {
        // Fetch market indices
        const infoResponse = await fetch('/api/dashboard/info')
        if (!infoResponse.ok) throw new Error('Failed to fetch market info')
        const infoData: DashboardInfo = await infoResponse.json()

        setMarketStatus(infoData.market_status)
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
            value: parseFloat(
              infoData.important_stocks['%5ENSEBANK'].last_price
            ),
            change: parseFloat(
              infoData.important_stocks['%5ENSEBANK'].points_change
            ),
            changePercent: parseFloat(
              infoData.important_stocks['%5ENSEBANK'].percentage_change
            )
          }
        ]
        setMarketIndices(indices)

        // Fetch pinned stocks
        await fetchPinnedStocks() // Call the function
      } catch (err) {
        setError('Failed to load market data. Please try again later.')
        toast.error('Failed to load market data')
      } finally {
        setIsDataLoading(false)
      }
    }

    if (isLoggedIn) {
      fetchDashboardData()
    }
  }, [isLoggedIn, fetchPinnedStocks]) // Added fetchPinnedStocks to dependency array

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    if (!input.trim()) return

    setIsLoading(true)
    try {
      const response = await fetch('/api/sessions/init', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: input.trim() })
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.error || 'Failed to create session')
      }

      const data = await response.json()
      router.push(
        `/chat/${data.session_id}?query=${encodeURIComponent(input.trim())}`
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

  const handleStockSearch = (e: React.FormEvent) => {
    e.preventDefault()
    if (stockSearch.trim()) {
      router.push(`/stocks/${stockSearch.trim().toUpperCase()}`)
    }
  }

  const handleStockClick = (symbol: string) => {
    router.push(`/stocks/${symbol}`)
  }

  // This function will be called by the overlay to trigger a refetch
  const handleStockAdded = () => {
    fetchPinnedStocks()
  }

  const handleDeleteStock = async (symbol: string) => {
    try {
      const response = await fetch('/api/dashboard/stocks/delete', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ symbol })
      })

      if (!response.ok) throw new Error('Failed to delete stock')
      setPinnedStocks(prev => prev.filter(stock => stock.symbol !== symbol))
      toast.success(`Stock ${symbol} removed successfully`)
    } catch (error) {
      toast.error('Failed to remove stock')
    }
  }

  const marketStatusInfo = getMarketStatusInfo(marketStatus)

  if (isAuthLoading || isDataLoading) {
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
      {/* Page Header */}
      <div className="bg-gradient-to-r from-blue-50 to-indigo-50 border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">
                Market Dashboard
              </h1>
              <p className="text-sm text-gray-600 mt-1">
                {currentTime &&
                  `Last updated: ${new Date(currentTime).toLocaleString(
                    'en-IN'
                  )}`}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Market Overview */}
      <section className="border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-xl font-semibold text-gray-900">
              Market Overview
            </h2>
            <div className="flex items-center gap-2 text-sm text-gray-600">
              <Globe className="h-4 w-4" />
              Indian Markets
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {marketIndices.map(index => (
              <Card
                key={index.name}
                className="hover:shadow-lg transition-all duration-200 border-0 shadow-md"
              >
                <CardContent className="p-6">
                  <div className="flex justify-between items-start">
                    <div className="flex-1">
                      <h3 className="font-semibold text-gray-700 text-sm uppercase tracking-wide">
                        {index.name}
                      </h3>
                      <p className="text-3xl font-bold mt-2 text-gray-900">
                        {index.value.toLocaleString('en-IN')}
                      </p>
                    </div>
                    <div
                      className={`flex items-center space-x-1 px-3 py-1 rounded-full text-sm font-medium ${
                        index.change >= 0
                          ? 'text-green-700 bg-green-100'
                          : 'text-red-700 bg-red-100'
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
                        index.change >= 0 ? 'text-green-600' : 'text-red-600'
                      }`}
                    >
                      {index.change >= 0 ? '+' : ''}
                      {index.change.toFixed(2)} pts
                    </p>
                    <div className="flex items-center text-xs text-gray-500">
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

      {/* Main Content */}
      <div className="flex-1 max-w-7xl mx-auto w-full px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Left Column - Pinned Stocks */}
          <div className="lg:col-span-1 space-y-6">
            <Card className="shadow-md border-0">
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-4">
                <CardTitle className="text-lg font-semibold flex items-center">
                  <Star className="h-5 w-5 mr-2 text-yellow-500" />
                  Pinned Stocks
                </CardTitle>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setIsOverlayOpen(true)}
                  className="hover:bg-blue-50"
                >
                  <Plus className="h-4 w-4" />
                </Button>
              </CardHeader>
              <CardContent className="space-y-2">
                {pinnedStocks.length === 0 ? (
                  <div className="text-center py-8 text-gray-500">
                    <Star className="h-8 w-8 mx-auto mb-2 text-gray-300" />
                    <p className="text-sm">No pinned stocks yet</p>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => setIsOverlayOpen(true)}
                      className="mt-2"
                    >
                      Add your first stock
                    </Button>
                  </div>
                ) : (
                  pinnedStocks.map(stock => (
                    <div
                      key={stock.symbol}
                      className="flex justify-between items-center p-4 rounded-xl hover:bg-gray-50 cursor-pointer transition-colors border border-gray-100"
                    >
                      <div
                        className="flex-1"
                        onClick={() => handleStockClick(stock.symbol)}
                      >
                        <h4 className="font-semibold text-gray-900">
                          {stock.symbol}
                        </h4>
                        <p className="text-sm text-gray-500 truncate">
                          {stock.name}
                        </p>
                      </div>
                      <div className="text-right mr-3">
                        <p className="font-semibold text-gray-900">
                          ₹{stock.price.toLocaleString('en-IN')}
                        </p>
                        <p
                          className={`text-sm font-medium ${
                            stock.change >= 0
                              ? 'text-green-600'
                              : 'text-red-600'
                          }`}
                        >
                          {stock.change >= 0 ? '+' : ''}
                          {stock.changePercent.toFixed(2)}%
                        </p>
                      </div>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleDeleteStock(stock.symbol)}
                        className="text-gray-400 hover:text-red-500"
                      >
                        ×
                      </Button>
                    </div>
                  ))
                )}
              </CardContent>
            </Card>

            {/* Quick Actions */}
            <Card className="shadow-md border-0">
              <CardHeader>
                <CardTitle className="text-lg font-semibold">
                  Quick Actions
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <Button
                  variant="outline"
                  className="w-full justify-start hover:bg-blue-50"
                  onClick={() => router.push('/portfolio')}
                >
                  <BarChart3 className="h-4 w-4 mr-2" />
                  View Portfolio
                </Button>
                <Button
                  variant="outline"
                  className="w-full justify-start hover:bg-yellow-50"
                  onClick={() => router.push('/watchlist')}
                >
                  <Star className="h-4 w-4 mr-2" />
                  Manage Watchlist
                </Button>
                <Button
                  variant="outline"
                  className="w-full justify-start hover:bg-green-50"
                  onClick={() => router.push('/news')}
                >
                  <Globe className="h-4 w-4 mr-2" />
                  Market News
                </Button>
              </CardContent>
            </Card>
          </div>

          {/* Right Column - AI Chat Welcome */}
          <div className="lg:col-span-2">
            <Card className="shadow-md border-0 h-fit">
              <CardContent className="p-8">
                <div className="text-center mb-8">
                  <div className="inline-flex items-center justify-center w-20 h-20 bg-gradient-to-br from-blue-500 to-purple-600 rounded-2xl mb-6">
                    <Sparkles className="h-10 w-10 text-white" />
                  </div>
                  <h1 className="text-4xl font-bold mb-3 bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
                    Welcome to Zenfi AI
                  </h1>
                  <p className="text-xl text-gray-600 mb-8 max-w-2xl mx-auto">
                    Your intelligent finance assistant for smarter investment
                    decisions
                  </p>
                </div>

                {/* Feature Grid */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div className="p-6 bg-gradient-to-br from-blue-50 to-blue-100 rounded-2xl">
                    <BarChart3 className="h-10 w-10 text-blue-600 mb-3" />
                    <h3 className="font-semibold text-lg mb-2">
                      Market Analysis
                    </h3>
                    <p className="text-sm text-gray-600">
                      Get AI-powered insights on market trends and stock
                      performance
                    </p>
                  </div>
                  <div className="p-6 bg-gradient-to-br from-green-50 to-green-100 rounded-2xl">
                    <TrendingUp className="h-10 w-10 text-green-600 mb-3" />
                    <h3 className="font-semibold text-lg mb-2">
                      Investment Advice
                    </h3>
                    <p className="text-sm text-gray-600">
                      Receive personalized investment recommendations
                    </p>
                  </div>
                  <div className="p-6 bg-gradient-to-br from-purple-50 to-purple-100 rounded-2xl">
                    <Activity className="h-10 w-10 text-purple-600 mb-3" />
                    <h3 className="font-semibold text-lg mb-2">
                      Portfolio Tracking
                    </h3>
                    <p className="text-sm text-gray-600">
                      Monitor your investments and track performance
                    </p>
                  </div>
                  <div className="p-6 bg-gradient-to-br from-orange-50 to-orange-100 rounded-2xl">
                    <Globe className="h-10 w-10 text-orange-600 mb-3" />
                    <h3 className="font-semibold text-lg mb-2">Market News</h3>
                    <p className="text-sm text-gray-600">
                      Stay updated with latest financial news and events
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>

      {/* Enhanced Fixed Chat Input */}
      <div className="fixed bottom-0 left-0 w-full bg-white/80 backdrop-blur-md border-t">
        <div className="mx-auto max-w-4xl px-4 py-4">
          <form onSubmit={handleSubmit} className="relative">
            <div className="relative rounded-2xl bg-white border-2 border-gray-200 shadow-xl overflow-hidden focus-within:border-blue-500 transition-colors">
              <Textarea
                name="input"
                rows={1}
                maxRows={4}
                placeholder="Ask me anything about stocks, markets, or your portfolio..."
                value={input}
                onChange={e => setInput(e.target.value)}
                className="w-full resize-none bg-transparent placeholder:text-gray-400 focus:outline-none py-4 px-6 pr-16 text-base"
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
              <button
                type="submit"
                disabled={isLoading || input.trim().length === 0}
                className="absolute right-3 bottom-3 bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700 text-white rounded-xl p-2.5 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200 shadow-lg"
              >
                {isLoading ? (
                  <div className="animate-spin rounded-full h-5 w-5 border-2 border-white border-t-transparent"></div>
                ) : (
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    width="20"
                    height="20"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  >
                    <path d="M5 12h14" />
                    <path d="M12 5l7 7-7 7" />
                  </svg>
                )}
              </button>
            </div>
            <p className="text-xs text-gray-500 mt-2 text-center">
              Press Enter to send, Shift + Enter for new line
            </p>
          </form>
        </div>
      </div>

      {/* Add Stock Overlay */}
      <AddStockOverlay
        isOpen={isOverlayOpen}
        onClose={() => setIsOverlayOpen(false)}
        onStockAdded={handleStockAdded} // Updated prop
      />
    </div>
  )
}
