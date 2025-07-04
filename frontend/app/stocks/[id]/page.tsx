'use client'

import { useParams, useRouter } from 'next/navigation'
import { useEffect, useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Separator } from '@/components/ui/separator'
import { toast } from 'sonner'
import dynamic from 'next/dynamic'
import {
  ArrowUp,
  ArrowDown,
  TrendingUp,
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
  Info,
  Newspaper,
  LineChart,
  CandlestickChart
} from 'lucide-react'
import { ApexOptions } from 'apexcharts'

// Dynamically import Chart with SSR disabled
const Chart = dynamic(() => import('react-apexcharts'), {
  ssr: false
})

// Interfaces remain the same
interface ChartDataPoint {
  date: string
  timestamp: number
  close: number
  high: number
  low: number
  open: number
  volume: number
}

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
  news: {
    data: {
      tickerStream: {
        stream: Array<{
          id: string
          content: {
            title: string
            summary: string
            pubDate: string
            thumbnail?: {
              resolutions: Array<{ url: string }>
            }
            canonicalUrl: { url: string }
          }
        }>
      }
    }
  }
  charts_data: string
}

export default function StockPage() {
  const params = useParams()
  const router = useRouter()
  const [stockInfo, setStockInfo] = useState<StockInfo | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [isPinned, setIsPinned] = useState(false)
  const [chartData, setChartData] = useState<ChartDataPoint[]>([])
  const [chartType, setChartType] = useState<'line' | 'candlestick'>(
    'candlestick'
  )

  const symbol = params.id as string

  useEffect(() => {
    const fetchStockInfo = async () => {
      if (!symbol) return

      setIsLoading(true)
      setError(null)

      try {
        const response = await fetch('/api/stocks/info', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ symbol: symbol.toUpperCase() })
        })

        if (!response.ok) throw new Error('Failed to fetch stock information')

        const data = await response.json()
        setStockInfo(data)
        if (data.charts_data) {
          const parsedData = parseChartData(
            data.charts_data,
            symbol.toUpperCase()
          )
          setChartData(parsedData)
        }
      } catch (err) {
        setError('Failed to load stock information. Please try again.')
        toast.error('Failed to load stock data')
      } finally {
        setIsLoading(false)
      }
    }

    fetchStockInfo()
  }, [symbol])

  const parseChartData = (
    chartsData: string,
    symbol: string
  ): ChartDataPoint[] => {
    const data = JSON.parse(chartsData)
    const timestamps = Object.keys(data).map(ts => parseInt(ts))
    timestamps.sort((a, b) => a - b)
    return timestamps.map(timestamp => {
      const date = new Date(timestamp).toLocaleDateString()
      const values = data[timestamp.toString()]
      return {
        date,
        timestamp,
        close: values[`('Close', '${symbol}')`],
        high: values[`('High', '${symbol}')`],
        low: values[`('Low', '${symbol}')`],
        open: values[`('Open', '${symbol}')`],
        volume: values[`('Volume', '${symbol}')`]
      }
    })
  }

  const formatCurrency = (value?: number, currency: string = 'INR') => {
    if (typeof value !== 'number' || isNaN(value)) return '-'
    return currency === 'INR'
      ? `₹${value.toLocaleString('en-IN')}`
      : `$${value.toLocaleString('en-US')}`
  }

  const formatLargeNumber = (value?: number) => {
    if (typeof value !== 'number' || isNaN(value)) return '-'
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
      const response = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
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

  const chartOptions: ApexOptions = {
    chart: {
      id: 'stock-price-chart',
      type: chartType,
      height: 400,
      toolbar: { show: true }
    },
    xaxis: {
      type: 'datetime',
      labels: { format: 'MMM dd' },
      title: { text: 'Date' }
    },
    yaxis: {
      title: { text: 'Price' },
      labels: {
        formatter: (value: number) =>
          formatCurrency(value, stockInfo?.stock_information.currency)
      }
    },
    plotOptions: {
      candlestick: {
        colors: {
          upward: 'hsl(var(--chart-1))',
          downward: 'hsl(var(--chart-2))'
        }
      }
    },
    tooltip: {
      x: { format: 'dd MMM yyyy' },
      y: {
        formatter: (value: number) =>
          formatCurrency(value, stockInfo?.stock_information.currency)
      }
    },
    stroke: {
      curve: 'smooth',
      width: chartType === 'line' ? 2 : 1
    }
  }

  const chartSeries =
    chartType === 'candlestick'
      ? [
          {
            name: 'Stock Price',
            data: chartData.map(data => ({
              x: data.timestamp,
              y: [data.open, data.high, data.low, data.close]
            }))
          }
        ]
      : [
          {
            name: 'Close Price',
            data: chartData.map(data => ({
              x: data.timestamp,
              y: data.close.toFixed(2)
            }))
          }
        ]

  if (isLoading) {
    return (
      <div className="min-h-screen">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="animate-pulse space-y-6">
            <div className="h-8 rounded w-1/4"></div>
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              <div className="lg:col-span-2 space-y-6">
                <div className="rounded-lg h-64"></div>
                <div className="rounded-lg h-48"></div>
              </div>
              <div className="space-y-6">
                <div className="rounded-lg h-32"></div>
                <div className="rounded-lg h-48"></div>
              </div>
            </div>
          </div>
        </div>
      </div>
    )
  }

  if (error || !stockInfo) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center space-y-4">
          <h1 className="text-2xl font-bold text-red-600">Error</h1>
          <p>{error || 'Stock not found'}</p>
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
    <div className="min-h-screen">
      <div className="sticky top-0 bg-background z-10">
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
                <h1 className="text-2xl font-bold">{stock.symbol}</h1>
                <p className="text-sm">{stock.shortName || stock.longName}</p>
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
        <Card className="shadow-sm border-0 mb-8">
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle className="flex items-center">
              <TrendingUp className="h-5 w-5 mr-2" />
              Price History
            </CardTitle>
            <div className="flex items-center space-x-2">
              <Button
                variant={chartType === 'line' ? 'default' : 'outline'}
                size="sm"
                onClick={() => setChartType('line')}
              >
                <LineChart className="h-4 w-4 sm:mr-2" />
                <span className="hidden sm:inline">Line</span>
              </Button>
              <Button
                variant={chartType === 'candlestick' ? 'default' : 'outline'}
                size="sm"
                onClick={() => setChartType('candlestick')}
              >
                <CandlestickChart className="h-4 w-4 sm:mr-2" />
                <span className="hidden sm:inline">Candle</span>
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            {chartData.length > 0 ? (
              <div style={{ width: '100%', height: 400 }}>
                <Chart
                  options={chartOptions}
                  series={chartSeries}
                  type={chartType}
                  height="100%"
                />
              </div>
            ) : (
              <p className="text-center">No historical data available</p>
            )}
          </CardContent>
        </Card>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          <div className="lg:col-span-2 space-y-6">
            <Card className="shadow-sm border-0">
              <CardContent className="p-6">
                <div className="flex items-center justify-between mb-6">
                  <div>
                    <div className="flex items-center space-x-3">
                      <h2 className="text-3xl font-bold">
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
                          ? 'text-green-800'
                          : 'text-gray-800'
                      }`}
                    >
                      <Activity className="h-3 w-3 mr-1" />
                      {stock.marketState === 'REGULAR'
                        ? 'Market Open'
                        : 'Market Closed'}
                    </div>
                    {stock.regularMarketTime && (
                      <p className="text-xs mt-1">
                        {new Date(
                          stock.regularMarketTime * 1000
                        ).toLocaleString()}
                      </p>
                    )}
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-6">
                  <div>
                    <h3 className="text-sm font-medium mb-2">Day Range</h3>
                    <div className="space-y-1">
                      <div className="flex justify-between text-sm">
                        <span>Low</span>
                        <span className="font-medium">
                          {formatCurrency(stock.dayLow, stock.currency)}
                        </span>
                      </div>
                      <div className="flex justify-between text-sm">
                        <span>High</span>
                        <span className="font-medium">
                          {formatCurrency(stock.dayHigh, stock.currency)}
                        </span>
                      </div>
                    </div>
                  </div>
                  <div>
                    <h3 className="text-sm font-medium mb-2">52 Week Range</h3>
                    <div className="space-y-1">
                      <div className="flex justify-between text-sm">
                        <span>Low</span>
                        <span className="font-medium">
                          {formatCurrency(
                            stock.fiftyTwoWeekLow,
                            stock.currency
                          )}
                        </span>
                      </div>
                      <div className="flex justify-between text-sm">
                        <span>High</span>
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

            <Card className="shadow-sm border">
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
                        <p className="text-sm">Beta</p>
                        <p className="font-semibold">{stock.beta.toFixed(2)}</p>
                      </div>
                    )}
                  </div>
                  <div className="space-y-4">
                    {stock.trailingPE && (
                      <div>
                        <p className="text-sm">P/E Ratio</p>
                        <p className="font-semibold">
                          {stock.trailingPE.toFixed(2)}
                        </p>
                      </div>
                    )}
                    {stock.dividendYield && (
                      <div>
                        <p className="text-sm">Dividend Yield</p>
                        <p className="font-semibold">
                          {(stock.dividendYield * 100).toFixed(2)}%
                        </p>
                      </div>
                    )}
                    {stock.bookValue && (
                      <div>
                        <p className="text-sm">Book Value</p>
                        <p className="font-semibold">
                          {formatCurrency(stock.bookValue, stock.currency)}
                        </p>
                      </div>
                    )}
                  </div>
                  <div className="space-y-4">
                    {stock.returnOnEquity && (
                      <div>
                        <p className="text-sm">ROE</p>
                        <p className="font-semibold">
                          {(stock.returnOnEquity * 100).toFixed(2)}%
                        </p>
                      </div>
                    )}
                    {stock.profitMargins && (
                      <div>
                        <p className="text-sm">Profit Margin</p>
                        <p className="font-semibold">
                          {(stock.profitMargins * 100).toFixed(2)}%
                        </p>
                      </div>
                    )}
                    {stock.debtToEquity && (
                      <div>
                        <p className="text-sm">Debt to Equity</p>
                        <p className="font-semibold">
                          {stock.debtToEquity.toFixed(2)}
                        </p>
                      </div>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>

            {stock.longBusinessSummary && (
              <Card className="shadow-sm border">
                <CardHeader>
                  <CardTitle className="flex items-center">
                    <Info className="h-5 w-5 mr-2" />
                    Company Overview
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="leading-relaxed">{stock.longBusinessSummary}</p>
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

            {stockInfo.news?.data?.tickerStream?.stream?.length > 0 && (
              <Card className="shadow-sm border">
                <CardHeader>
                  <CardTitle className="flex items-center">
                    <Newspaper className="h-5 w-5 mr-2" />
                    Latest News
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-6">
                    {stockInfo.news.data.tickerStream.stream
                      .slice(0, 5)
                      .map((newsItem, index) => (
                        <div key={index} className="flex space-x-4">
                          {newsItem.content.thumbnail?.resolutions[0]?.url && (
                            <img
                              src={
                                newsItem.content.thumbnail.resolutions[0].url
                              }
                              alt={newsItem.content.title}
                              className="w-24 h-16 object-cover rounded"
                            />
                          )}
                          <div>
                            <h3 className="text-sm font-medium">
                              {newsItem.content.title}
                            </h3>
                            <p className="text-xs text-gray-500">
                              {newsItem.content.summary}
                            </p>
                            <a
                              href={newsItem.content.canonicalUrl.url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-xs text-blue-600 hover:underline"
                            >
                              Read more
                            </a>
                          </div>
                        </div>
                      ))}
                  </div>
                </CardContent>
              </Card>
            )}
          </div>

          <div className="space-y-6">
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
                        <span className="text-sm">Price Target</span>
                        <span className="font-medium">
                          {formatCurrency(
                            stock.targetMeanPrice,
                            stock.currency
                          )}
                        </span>
                      </div>
                      {stock.targetHighPrice && stock.targetLowPrice && (
                        <div className="text-xs">
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
                    <MapPin className="h-4 w-4 mt-0.5" />
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
                    <Phone className="h-4 w-4" />
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
                          <p className="text-xs">{officer.title}</p>
                        </div>
                        {officer.age && (
                          <span className="text-xs">Age {officer.age}</span>
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
