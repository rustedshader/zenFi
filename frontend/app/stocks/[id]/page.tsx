'use client'

import { useParams, useRouter } from 'next/navigation'
import { useEffect, useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Separator } from '@/components/ui/separator'
import { toast } from 'sonner'
import {
  ArrowUp,
  ArrowDown,
  TrendingUp,
  TrendingDown,
  DollarSign,
  BarChart3,
  Calendar,
  Globe,
  Building,
  Phone,
  MapPin,
  Star,
  StarOff,
  Activity,
  Users,
  Target,
  Briefcase,
  Clock,
  ChevronLeft,
  ExternalLink,
  Info
} from 'lucide-react'

interface StockInfo {
  stock_information: {
    symbol: string
    shortName: string
    longName: string
    currentPrice: number
    previousClose: number
    regularMarketChange: number
    regularMarketChangePercent: number
    dayLow: number
    dayHigh: number
    fiftyTwoWeekLow: number
    fiftyTwoWeekHigh: number
    volume: number
    averageVolume: number
    marketCap: number
    trailingPE?: number
    forwardPE?: number
    dividendRate?: number
    dividendYield?: number
    beta?: number
    bookValue?: number
    priceToBook?: number
    trailingEps?: number
    forwardEps?: number
    targetMeanPrice?: number
    targetHighPrice?: number
    targetLowPrice?: number
    recommendationMean?: number
    recommendationKey?: string
    numberOfAnalystOpinions?: number
    totalRevenue?: number
    grossProfits?: number
    operatingMargins?: number
    profitMargins?: number
    returnOnAssets?: number
    returnOnEquity?: number
    totalDebt?: number
    totalCash?: number
    debtToEquity?: number
    currency: string
    industry?: string
    sector?: string
    longBusinessSummary?: string
    website?: string
    address1?: string
    address2?: string
    city?: string
    country?: string
    phone?: string
    companyOfficers?: Array<{
      name: string
      title: string
      age?: number
      totalPay?: number
    }>
    regularMarketTime?: number
    marketState?: string
  }
  yahoo_finance_news?: string
  duckduckgo_finance_news?: string
}

export default function StockPage() {
  const params = useParams()
  const router = useRouter()
  const [stockInfo, setStockInfo] = useState<StockInfo | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [isPinned, setIsPinned] = useState(false)

  const symbol = params.id as string

  useEffect(() => {
    const fetchStockInfo = async () => {
      if (!symbol) return

      setIsLoading(true)
      setError(null)

      try {
        const response = await fetch('/api/stocks/info', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({ symbol: symbol.toUpperCase() })
        })

        if (!response.ok) {
          throw new Error('Failed to fetch stock information')
        }

        const data = await response.json()
        console.log(data)
        setStockInfo(data)
      } catch (err) {
        setError('Failed to load stock information. Please try again.')
        toast.error('Failed to load stock data')
      } finally {
        setIsLoading(false)
      }
    }

    fetchStockInfo()
  }, [symbol])

  const formatCurrency = (value?: number, currency: string = 'INR') => {
    if (typeof value !== 'number' || isNaN(value)) {
      return '-'
    }
    if (currency === 'INR') {
      return `₹${value.toLocaleString('en-IN')}`
    }
    return `$${value.toLocaleString('en-US')}`
  }

  const formatLargeNumber = (value?: number) => {
    if (typeof value !== 'number' || isNaN(value)) {
      return '-'
    }
    if (value >= 1e12) return `₹${(value / 1e12).toFixed(2)}T`
    if (value >= 1e9) return `₹${(value / 1e9).toFixed(2)}B`
    if (value >= 1e7) return `₹${(value / 1e7).toFixed(2)}Cr`
    if (value >= 1e5) return `₹${(value / 1e5).toFixed(2)}L`
    return `₹${value.toLocaleString('en-IN')}`
  }

  const getRecommendationColor = (key?: string) => {
    switch (key?.toLowerCase()) {
      case 'strong_buy':
      case 'buy':
        return 'bg-green-100 text-green-800'
      case 'hold':
        return 'bg-yellow-100 text-yellow-800'
      case 'sell':
      case 'strong_sell':
        return 'bg-red-100 text-red-800'
      default:
        return 'bg-gray-100 text-gray-800'
    }
  }

  const handlePinStock = async () => {
    try {
      const endpoint = isPinned
        ? '/api/dashboard/stocks/delete'
        : '/api/dashboard/stocks'
      const method = 'POST'

      const response = await fetch(endpoint, {
        method,
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ symbol: symbol.toUpperCase() })
      })

      if (!response.ok) throw new Error('Failed to update stock')

      setIsPinned(!isPinned)
      toast.success(
        isPinned ? 'Stock removed from watchlist' : 'Stock added to watchlist'
      )
    } catch (error) {
      toast.error('Failed to update watchlist')
    }
  }

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="animate-pulse space-y-6">
            <div className="h-8 bg-gray-200 rounded w-1/4"></div>
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              <div className="lg:col-span-2 space-y-6">
                <div className="bg-white rounded-lg h-64"></div>
                <div className="bg-white rounded-lg h-48"></div>
              </div>
              <div className="space-y-6">
                <div className="bg-white rounded-lg h-32"></div>
                <div className="bg-white rounded-lg h-48"></div>
              </div>
            </div>
          </div>
        </div>
      </div>
    )
  }

  if (error || !stockInfo) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center space-y-4">
          <h1 className="text-2xl font-bold text-red-600">Error</h1>
          <p className="text-gray-600">{error || 'Stock not found'}</p>
          <Button onClick={() => router.back()} variant="outline">
            <ChevronLeft className="h-4 w-4 mr-2" />
            Go Back
          </Button>
        </div>
      </div>
    )
  }

  const stock = stockInfo.stock_information
  const isPositive = stock.regularMarketChange >= 0
  const changePercent = Math.abs(stock.regularMarketChangePercent)

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => router.back()}
                className="hover:bg-gray-100"
              >
                <ChevronLeft className="h-4 w-4 mr-1" />
                Back
              </Button>
              <div>
                <h1 className="text-2xl font-bold text-gray-900">
                  {stock.symbol}
                </h1>
                <p className="text-sm text-gray-600">
                  {stock.shortName || stock.longName}
                </p>
              </div>
            </div>
            <div className="flex items-center space-x-3">
              <Button
                variant="outline"
                size="sm"
                onClick={handlePinStock}
                className="hover:bg-yellow-50"
              >
                {isPinned ? (
                  <Star className="h-4 w-4 mr-2 fill-yellow-400 text-yellow-400" />
                ) : (
                  <StarOff className="h-4 w-4 mr-2" />
                )}
                {isPinned ? 'Unpin' : 'Pin'}
              </Button>
              {stock.website && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => window.open(stock.website, '_blank')}
                  className="hover:bg-blue-50"
                >
                  <ExternalLink className="h-4 w-4 mr-2" />
                  Website
                </Button>
              )}
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Main Content */}
          <div className="lg:col-span-2 space-y-6">
            {/* Price Card */}
            <Card className="shadow-sm border-0">
              <CardContent className="p-6">
                <div className="flex items-center justify-between mb-6">
                  <div>
                    <div className="flex items-center space-x-3">
                      <h2 className="text-3xl font-bold text-gray-900">
                        {formatCurrency(stock.currentPrice, stock.currency)}
                      </h2>
                      <div
                        className={`flex items-center space-x-1 px-3 py-1 rounded-full text-sm font-medium ${
                          isPositive
                            ? 'text-green-700 bg-green-100'
                            : 'text-red-700 bg-red-100'
                        }`}
                      >
                        {isPositive ? (
                          <ArrowUp className="h-3 w-3" />
                        ) : (
                          <ArrowDown className="h-3 w-3" />
                        )}
                        <span>
                          {formatCurrency(
                            Math.abs(stock.regularMarketChange),
                            stock.currency
                          )}{' '}
                          ({changePercent.toFixed(2)}%)
                        </span>
                      </div>
                    </div>
                    <p className="text-sm text-gray-500 mt-1">
                      Previous Close:{' '}
                      {formatCurrency(stock.previousClose, stock.currency)}
                    </p>
                  </div>
                  <div className="text-right">
                    <div
                      className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-medium ${
                        stock.marketState === 'REGULAR'
                          ? 'bg-green-100 text-green-800'
                          : 'bg-gray-100 text-gray-800'
                      }`}
                    >
                      <Activity className="h-3 w-3 mr-1" />
                      {stock.marketState === 'REGULAR'
                        ? 'Market Open'
                        : 'Market Closed'}
                    </div>
                    {stock.regularMarketTime && (
                      <p className="text-xs text-gray-500 mt-1">
                        {new Date(
                          stock.regularMarketTime * 1000
                        ).toLocaleString()}
                      </p>
                    )}
                  </div>
                </div>

                {/* Day Range */}
                <div className="grid grid-cols-2 gap-6">
                  <div>
                    <h3 className="text-sm font-medium text-gray-700 mb-2">
                      Day Range
                    </h3>
                    <div className="space-y-1">
                      <div className="flex justify-between text-sm">
                        <span className="text-gray-500">Low</span>
                        <span className="font-medium">
                          {formatCurrency(stock.dayLow, stock.currency)}
                        </span>
                      </div>
                      <div className="flex justify-between text-sm">
                        <span className="text-gray-500">High</span>
                        <span className="font-medium">
                          {formatCurrency(stock.dayHigh, stock.currency)}
                        </span>
                      </div>
                    </div>
                  </div>
                  <div>
                    <h3 className="text-sm font-medium text-gray-700 mb-2">
                      52 Week Range
                    </h3>
                    <div className="space-y-1">
                      <div className="flex justify-between text-sm">
                        <span className="text-gray-500">Low</span>
                        <span className="font-medium">
                          {formatCurrency(
                            stock.fiftyTwoWeekLow,
                            stock.currency
                          )}
                        </span>
                      </div>
                      <div className="flex justify-between text-sm">
                        <span className="text-gray-500">High</span>
                        <span className="font-medium">
                          {formatCurrency(
                            stock.fiftyTwoWeekHigh,
                            stock.currency
                          )}
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Key Statistics */}
            <Card className="shadow-sm border-0">
              <CardHeader>
                <CardTitle className="flex items-center">
                  <BarChart3 className="h-5 w-5 mr-2" />
                  Key Statistics
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 md:grid-cols-3 gap-6">
                  <div className="space-y-4">
                    <div>
                      <p className="text-sm text-gray-500">Market Cap</p>
                      <p className="font-semibold">
                        {formatLargeNumber(stock.marketCap)}
                      </p>
                    </div>
                    <div>
                      <p className="text-sm text-gray-500">Volume</p>
                      <p className="font-semibold">
                        {typeof stock.volume === 'number' &&
                        !isNaN(stock.volume)
                          ? stock.volume.toLocaleString()
                          : '-'}
                      </p>
                    </div>
                    {stock.beta && (
                      <div>
                        <p className="text-sm text-gray-500">Beta</p>
                        <p className="font-semibold">{stock.beta.toFixed(2)}</p>
                      </div>
                    )}
                  </div>
                  <div className="space-y-4">
                    {stock.trailingPE && (
                      <div>
                        <p className="text-sm text-gray-500">P/E Ratio</p>
                        <p className="font-semibold">
                          {stock.trailingPE.toFixed(2)}
                        </p>
                      </div>
                    )}
                    {stock.dividendYield && (
                      <div>
                        <p className="text-sm text-gray-500">Dividend Yield</p>
                        <p className="font-semibold">
                          {(stock.dividendYield * 100).toFixed(2)}%
                        </p>
                      </div>
                    )}
                    {stock.bookValue && (
                      <div>
                        <p className="text-sm text-gray-500">Book Value</p>
                        <p className="font-semibold">
                          {formatCurrency(stock.bookValue, stock.currency)}
                        </p>
                      </div>
                    )}
                  </div>
                  <div className="space-y-4">
                    {stock.returnOnEquity && (
                      <div>
                        <p className="text-sm text-gray-500">ROE</p>
                        <p className="font-semibold">
                          {(stock.returnOnEquity * 100).toFixed(2)}%
                        </p>
                      </div>
                    )}
                    {stock.profitMargins && (
                      <div>
                        <p className="text-sm text-gray-500">Profit Margin</p>
                        <p className="font-semibold">
                          {(stock.profitMargins * 100).toFixed(2)}%
                        </p>
                      </div>
                    )}
                    {stock.debtToEquity && (
                      <div>
                        <p className="text-sm text-gray-500">Debt to Equity</p>
                        <p className="font-semibold">
                          {stock.debtToEquity.toFixed(2)}
                        </p>
                      </div>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Company Overview */}
            {stock.longBusinessSummary && (
              <Card className="shadow-sm border-0">
                <CardHeader>
                  <CardTitle className="flex items-center">
                    <Info className="h-5 w-5 mr-2" />
                    Company Overview
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-gray-700 leading-relaxed">
                    {stock.longBusinessSummary}
                  </p>
                  {(stock.industry || stock.sector) && (
                    <div className="flex items-center space-x-4 mt-4 pt-4 border-t">
                      {stock.sector && (
                        <Badge
                          variant="secondary"
                          className="flex items-center"
                        >
                          <Briefcase className="h-3 w-3 mr-1" />
                          {stock.sector}
                        </Badge>
                      )}
                      {stock.industry && (
                        <Badge variant="outline" className="flex items-center">
                          <Building className="h-3 w-3 mr-1" />
                          {stock.industry}
                        </Badge>
                      )}
                    </div>
                  )}
                </CardContent>
              </Card>
            )}
          </div>

          {/* Sidebar */}
          <div className="space-y-6">
            {/* Analyst Recommendations */}
            {stock.recommendationKey && (
              <Card className="shadow-sm border-0">
                <CardHeader>
                  <CardTitle className="flex items-center">
                    <Target className="h-5 w-5 mr-2" />
                    Analyst Rating
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="text-center">
                    <Badge
                      className={`text-lg px-4 py-2 ${getRecommendationColor(
                        stock.recommendationKey
                      )}`}
                    >
                      {stock.recommendationKey.replace('_', ' ').toUpperCase()}
                    </Badge>
                    {stock.numberOfAnalystOpinions && (
                      <p className="text-sm text-gray-500 mt-2">
                        Based on {stock.numberOfAnalystOpinions} analyst
                        opinions
                      </p>
                    )}
                  </div>

                  {stock.targetMeanPrice && (
                    <div className="space-y-2">
                      <div className="flex justify-between">
                        <span className="text-sm text-gray-500">
                          Price Target
                        </span>
                        <span className="font-medium">
                          {formatCurrency(
                            stock.targetMeanPrice,
                            stock.currency
                          )}
                        </span>
                      </div>
                      {stock.targetHighPrice && stock.targetLowPrice && (
                        <div className="text-xs text-gray-500">
                          Range:{' '}
                          {formatCurrency(stock.targetLowPrice, stock.currency)}{' '}
                          -{' '}
                          {formatCurrency(
                            stock.targetHighPrice,
                            stock.currency
                          )}
                        </div>
                      )}
                    </div>
                  )}
                </CardContent>
              </Card>
            )}

            {/* Company Details */}
            <Card className="shadow-sm border-0">
              <CardHeader>
                <CardTitle className="flex items-center">
                  <Building className="h-5 w-5 mr-2" />
                  Company Details
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                {(stock.address1 || stock.city || stock.country) && (
                  <div className="flex items-start space-x-2">
                    <MapPin className="h-4 w-4 mt-0.5 text-gray-400" />
                    <div className="text-sm">
                      {stock.address1 && <div>{stock.address1}</div>}
                      {stock.address2 && <div>{stock.address2}</div>}
                      <div>
                        {[stock.city, stock.country].filter(Boolean).join(', ')}
                      </div>
                    </div>
                  </div>
                )}

                {stock.phone && (
                  <div className="flex items-center space-x-2">
                    <Phone className="h-4 w-4 text-gray-400" />
                    <span className="text-sm">{stock.phone}</span>
                  </div>
                )}

                {stock.website && (
                  <div className="flex items-center space-x-2">
                    <Globe className="h-4 w-4 text-gray-400" />
                    <a
                      href={stock.website}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-sm text-blue-600 hover:underline"
                    >
                      {stock.website.replace(/(^\w+:|^)\/\//, '')}
                    </a>
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Key Executives */}
            {stock.companyOfficers && stock.companyOfficers.length > 0 && (
              <Card className="shadow-sm border-0">
                <CardHeader>
                  <CardTitle className="flex items-center">
                    <Users className="h-5 w-5 mr-2" />
                    Key Executives
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    {stock.companyOfficers.slice(0, 5).map((officer, index) => (
                      <div
                        key={index}
                        className="flex justify-between items-start"
                      >
                        <div>
                          <p className="font-medium text-sm">{officer.name}</p>
                          <p className="text-xs text-gray-500">
                            {officer.title}
                          </p>
                        </div>
                        {officer.age && (
                          <span className="text-xs text-gray-400">
                            Age {officer.age}
                          </span>
                        )}
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
