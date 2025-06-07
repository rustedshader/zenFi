'use client'

import { useState, useEffect, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import {
  Plus,
  Star,
  Trash2,
  Grid3X3,
  Table,
  TrendingUp,
  TrendingDown,
  Eye,
  ArrowUpDown
} from 'lucide-react'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import {
  Table as TableComponent,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow
} from '@/components/ui/table'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger
} from '@/components/ui/alert-dialog'
import { toast } from 'sonner'
import AddStockOverlay from '@/components/homepage/add-stock-overlay'

interface Stock {
  symbol: string
  name: string
  price: number
  change: number
  changePercent: number
  currency: string
  dayHigh: number
  dayLow: number
  marketCap: number
  volume: number
  exchange: string
  yearHigh: number
  yearLow: number
  fiftyDayAverage: number
  twoHundredDayAverage: number
}

interface StockData {
  symbol: string
  fast_info: {
    currency: string
    lastPrice: number
    previousClose: number
    dayHigh: number
    dayLow: number
    marketCap: number
    lastVolume: number
    exchange: string
    yearHigh: number
    yearLow: number
    fiftyDayAverage: number
    twoHundredDayAverage: number
  }
  stock_points_change: string
  stocks_percentage_change: string
}

export default function WatchListPage() {
  const router = useRouter()
  const [stocks, setStocks] = useState<Stock[]>([])
  const [loading, setLoading] = useState(true)
  const [isOverlayOpen, setIsOverlayOpen] = useState(false)
  const [sortConfig, setSortConfig] = useState<{
    key: keyof Stock
    direction: 'asc' | 'desc'
  } | null>(null)

  const fetchwatchlistStocks = useCallback(async () => {
    try {
      setLoading(true)
      const response = await fetch('/api/dashboard/stocks')
      if (!response.ok) throw new Error('Failed to fetch stocks')

      const data: { stocks: StockData[] } = await response.json()

      const processedStocks: Stock[] = data.stocks.map(stock => ({
        symbol: stock.symbol,
        name: stock.symbol,
        price: stock.fast_info.lastPrice,
        change: parseFloat(stock.stock_points_change.replace(/[^-+0-9.]/g, '')),
        changePercent: parseFloat(
          stock.stocks_percentage_change.replace(/[^-+0-9.]/g, '')
        ),
        currency: stock.fast_info.currency,
        dayHigh: stock.fast_info.dayHigh,
        dayLow: stock.fast_info.dayLow,
        marketCap: stock.fast_info.marketCap,
        volume: stock.fast_info.lastVolume,
        exchange: stock.fast_info.exchange,
        yearHigh: stock.fast_info.yearHigh,
        yearLow: stock.fast_info.yearLow,
        fiftyDayAverage: stock.fast_info.fiftyDayAverage,
        twoHundredDayAverage: stock.fast_info.twoHundredDayAverage
      }))

      setStocks(processedStocks)
    } catch (error) {
      console.error('Failed to fetch watchlist stocks:', error)
      toast.error('Failed to load watchlist stocks')
    } finally {
      setLoading(false)
    }
  }, [])

  const handleDeleteStock = async (symbol: string) => {
    try {
      const response = await fetch('/api/dashboard/stocks/delete', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ symbol })
      })

      if (!response.ok) throw new Error('Failed to delete stock')

      setStocks(prev => prev.filter(stock => stock.symbol !== symbol))
      toast.success(`${symbol} removed from watchlist`)
    } catch (error) {
      toast.error('Failed to remove stock from watchlist')
    }
  }

  const handleStockAdded = () => {
    fetchwatchlistStocks()
  }

  const handleSort = (key: keyof Stock) => {
    let direction: 'asc' | 'desc' = 'asc'
    if (
      sortConfig &&
      sortConfig.key === key &&
      sortConfig.direction === 'asc'
    ) {
      direction = 'desc'
    }
    setSortConfig({ key, direction })
  }

  const sortedStocks = [...stocks].sort((a, b) => {
    if (!sortConfig) return 0

    const { key, direction } = sortConfig
    const aValue = a[key]
    const bValue = b[key]

    if (aValue < bValue) return direction === 'asc' ? -1 : 1
    if (aValue > bValue) return direction === 'asc' ? 1 : -1
    return 0
  })

  const formatCurrency = (value: number, currency: string) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: currency === 'INR' ? 'INR' : 'USD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    }).format(value)
  }

  const formatNumber = (value: number) => {
    if (value >= 1e12) return `${(value / 1e12).toFixed(2)}T`
    if (value >= 1e9) return `${(value / 1e9).toFixed(2)}B`
    if (value >= 1e6) return `${(value / 1e6).toFixed(2)}M`
    if (value >= 1e3) return `${(value / 1e3).toFixed(2)}K`
    return value.toLocaleString()
  }

  useEffect(() => {
    fetchwatchlistStocks()
  }, [fetchwatchlistStocks])

  if (loading) {
    return (
      <div className="container mx-auto p-6">
        <div className="mb-6">
          <Skeleton className="h-8 w-48 mb-2" />
          <Skeleton className="h-4 w-96" />
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {Array.from({ length: 6 }).map((_, i) => (
            <Card key={i} className="p-6">
              <Skeleton className="h-6 w-20 mb-4" />
              <Skeleton className="h-8 w-32 mb-2" />
              <Skeleton className="h-4 w-24 mb-4" />
              <div className="space-y-2">
                <Skeleton className="h-4 w-full" />
                <Skeleton className="h-4 w-full" />
                <Skeleton className="h-4 w-3/4" />
              </div>
            </Card>
          ))}
        </div>
      </div>
    )
  }

  return (
    <div className="container mx-auto p-6">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-3xl font-bold flex items-center gap-2">
            <Star className="h-8 w-8 text-yellow-500" />
            My Watchlist
          </h1>
          <p className="text-muted-foreground mt-1">
            Track your favorite stocks in one place
          </p>
        </div>
        <Button onClick={() => setIsOverlayOpen(true)} className="gap-2">
          <Plus className="h-4 w-4" />
          Add Stock
        </Button>
      </div>

      {stocks.length === 0 ? (
        <Card className="p-12 text-center">
          <Star className="h-16 w-16 mx-auto mb-4 text-gray-300" />
          <h3 className="text-xl font-semibold mb-2">
            Your Watchlist is empty
          </h3>
          <p className="text-muted-foreground mb-4">
            Start building your watchlist by adding stocks you're interested in
          </p>
          <Button onClick={() => setIsOverlayOpen(true)} className="gap-2">
            <Plus className="h-4 w-4" />
            Add Your First Stock
          </Button>
        </Card>
      ) : (
        <Tabs defaultValue="cards" className="w-full">
          <TabsList className="mb-6">
            <TabsTrigger value="cards" className="gap-2">
              <Grid3X3 className="h-4 w-4" />
              Cards View
            </TabsTrigger>
            <TabsTrigger value="table" className="gap-2">
              <Table className="h-4 w-4" />
              Table View
            </TabsTrigger>
          </TabsList>

          <TabsContent value="cards">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {stocks.map(stock => (
                <Card
                  key={stock.symbol}
                  className="hover:shadow-lg transition-shadow"
                >
                  <CardHeader className="pb-3">
                    <div className="flex justify-between items-start">
                      <div>
                        <CardTitle className="text-lg">
                          {stock.symbol}
                        </CardTitle>
                        <Badge variant="outline" className="mt-1">
                          {stock.exchange}
                        </Badge>
                      </div>
                      <div className="flex gap-1">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => router.push(`/stocks/${stock.symbol}`)}
                        >
                          <Eye className="h-4 w-4" />
                        </Button>
                        <AlertDialog>
                          <AlertDialogTrigger asChild>
                            <Button
                              variant="ghost"
                              size="sm"
                              className="text-red-500"
                            >
                              <Trash2 className="h-4 w-4" />
                            </Button>
                          </AlertDialogTrigger>
                          <AlertDialogContent>
                            <AlertDialogHeader>
                              <AlertDialogTitle>
                                Remove from watchlist
                              </AlertDialogTitle>
                              <AlertDialogDescription>
                                Are you sure you want to remove {stock.symbol}{' '}
                                from your watchlist?
                              </AlertDialogDescription>
                            </AlertDialogHeader>
                            <AlertDialogFooter>
                              <AlertDialogCancel>Cancel</AlertDialogCancel>
                              <AlertDialogAction
                                onClick={() => handleDeleteStock(stock.symbol)}
                                className="bg-red-500 hover:bg-red-600"
                              >
                                Remove
                              </AlertDialogAction>
                            </AlertDialogFooter>
                          </AlertDialogContent>
                        </AlertDialog>
                      </div>
                    </div>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-4">
                      <div>
                        <div className="text-2xl font-bold">
                          {formatCurrency(stock.price, stock.currency)}
                        </div>
                        <div
                          className={`flex items-center gap-1 text-sm font-medium ${
                            stock.changePercent >= 0
                              ? 'text-green-600'
                              : 'text-red-600'
                          }`}
                        >
                          {stock.changePercent >= 0 ? (
                            <TrendingUp className="h-4 w-4" />
                          ) : (
                            <TrendingDown className="h-4 w-4" />
                          )}
                          {stock.changePercent >= 0 ? '+' : ''}
                          {stock.changePercent.toFixed(2)}%
                          <span className="text-muted-foreground">
                            ({stock.change >= 0 ? '+' : ''}
                            {stock.change.toFixed(2)})
                          </span>
                        </div>
                      </div>

                      <div className="grid grid-cols-2 gap-4 text-sm">
                        <div>
                          <p className="text-muted-foreground">Day Range</p>
                          <p className="font-medium">
                            {stock.dayLow.toFixed(2)} -{' '}
                            {stock.dayHigh.toFixed(2)}
                          </p>
                        </div>
                        <div>
                          <p className="text-muted-foreground">Volume</p>
                          <p className="font-medium">
                            {formatNumber(stock.volume)}
                          </p>
                        </div>
                        <div>
                          <p className="text-muted-foreground">Market Cap</p>
                          <p className="font-medium">
                            {formatNumber(stock.marketCap)}
                          </p>
                        </div>
                        <div>
                          <p className="text-muted-foreground">52W High</p>
                          <p className="font-medium">
                            {stock.yearHigh.toFixed(2)}
                          </p>
                        </div>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          </TabsContent>

          <TabsContent value="table">
            <Card>
              <TableComponent>
                <TableHeader>
                  <TableRow>
                    <TableHead>
                      <Button
                        variant="ghost"
                        onClick={() => handleSort('symbol')}
                        className="h-auto p-0 font-semibold"
                      >
                        Symbol <ArrowUpDown className="ml-2 h-4 w-4" />
                      </Button>
                    </TableHead>
                    <TableHead>
                      <Button
                        variant="ghost"
                        onClick={() => handleSort('price')}
                        className="h-auto p-0 font-semibold"
                      >
                        Price <ArrowUpDown className="ml-2 h-4 w-4" />
                      </Button>
                    </TableHead>
                    <TableHead>
                      <Button
                        variant="ghost"
                        onClick={() => handleSort('changePercent')}
                        className="h-auto p-0 font-semibold"
                      >
                        Change % <ArrowUpDown className="ml-2 h-4 w-4" />
                      </Button>
                    </TableHead>
                    <TableHead>Day Range</TableHead>
                    <TableHead>
                      <Button
                        variant="ghost"
                        onClick={() => handleSort('volume')}
                        className="h-auto p-0 font-semibold"
                      >
                        Volume <ArrowUpDown className="ml-2 h-4 w-4" />
                      </Button>
                    </TableHead>
                    <TableHead>
                      <Button
                        variant="ghost"
                        onClick={() => handleSort('marketCap')}
                        className="h-auto p-0 font-semibold"
                      >
                        Market Cap <ArrowUpDown className="ml-2 h-4 w-4" />
                      </Button>
                    </TableHead>
                    <TableHead>52W Range</TableHead>
                    <TableHead>Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {sortedStocks.map(stock => (
                    <TableRow key={stock.symbol} className="hover:bg-muted/50">
                      <TableCell>
                        <div>
                          <div className="font-semibold">{stock.symbol}</div>
                          <Badge variant="outline" className="text-xs">
                            {stock.exchange}
                          </Badge>
                        </div>
                      </TableCell>
                      <TableCell>
                        <div className="font-semibold">
                          {formatCurrency(stock.price, stock.currency)}
                        </div>
                      </TableCell>
                      <TableCell>
                        <div
                          className={`flex items-center gap-1 font-medium ${
                            stock.changePercent >= 0
                              ? 'text-green-600'
                              : 'text-red-600'
                          }`}
                        >
                          {stock.changePercent >= 0 ? (
                            <TrendingUp className="h-4 w-4" />
                          ) : (
                            <TrendingDown className="h-4 w-4" />
                          )}
                          {stock.changePercent >= 0 ? '+' : ''}
                          {stock.changePercent.toFixed(2)}%
                        </div>
                      </TableCell>
                      <TableCell>
                        <div className="text-sm">
                          {stock.dayLow.toFixed(2)} - {stock.dayHigh.toFixed(2)}
                        </div>
                      </TableCell>
                      <TableCell>{formatNumber(stock.volume)}</TableCell>
                      <TableCell>{formatNumber(stock.marketCap)}</TableCell>
                      <TableCell>
                        <div className="text-sm">
                          {stock.yearLow.toFixed(2)} -{' '}
                          {stock.yearHigh.toFixed(2)}
                        </div>
                      </TableCell>
                      <TableCell>
                        <div className="flex gap-2">
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() =>
                              router.push(`/stocks/${stock.symbol}`)
                            }
                          >
                            <Eye className="h-4 w-4" />
                          </Button>
                          <AlertDialog>
                            <AlertDialogTrigger asChild>
                              <Button
                                variant="ghost"
                                size="sm"
                                className="text-red-500"
                              >
                                <Trash2 className="h-4 w-4" />
                              </Button>
                            </AlertDialogTrigger>
                            <AlertDialogContent>
                              <AlertDialogHeader>
                                <AlertDialogTitle>
                                  Remove from watchlist
                                </AlertDialogTitle>
                                <AlertDialogDescription>
                                  Are you sure you want to remove {stock.symbol}{' '}
                                  from your watchlist?
                                </AlertDialogDescription>
                              </AlertDialogHeader>
                              <AlertDialogFooter>
                                <AlertDialogCancel>Cancel</AlertDialogCancel>
                                <AlertDialogAction
                                  onClick={() =>
                                    handleDeleteStock(stock.symbol)
                                  }
                                  className="bg-red-500 hover:bg-red-600"
                                >
                                  Remove
                                </AlertDialogAction>
                              </AlertDialogFooter>
                            </AlertDialogContent>
                          </AlertDialog>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </TableComponent>
            </Card>
          </TabsContent>
        </Tabs>
      )}

      <AddStockOverlay
        isOpen={isOverlayOpen}
        onClose={() => setIsOverlayOpen(false)}
        onStockAdded={handleStockAdded}
      />
    </div>
  )
}
