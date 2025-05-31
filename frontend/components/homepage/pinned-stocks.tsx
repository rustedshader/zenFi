'use client'
import { Plus, Star } from 'lucide-react'
import { Card, CardHeader, CardTitle, CardContent } from '../ui/card'
import { Button } from '../ui/button'
import { Skeleton } from '../ui/skeleton'
import { useCallback, useEffect, useState } from 'react'
import { toast } from 'sonner'
import { useRouter } from 'next/navigation'
import AddStockOverlay from './add-stock-overlay'

interface Stock {
  symbol: string
  name: string
  price: number
  change: number
  changePercent: number
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

export default function PinnedStocks() {
  const router = useRouter()
  const [pinnedStocks, setPinnedStocks] = useState<Stock[]>([])
  const [isOverlayOpen, setIsOverlayOpen] = useState(false)
  const [loading, setLoading] = useState<boolean>(true)

  const handleStockClick = (symbol: string) => {
    router.push(`/stocks/${symbol}`)
  }

  const handleStockAdded = () => {
    fetchPinnedStocks()
  }

  const fetchPinnedStocks = useCallback(async () => {
    try {
      setLoading(true)
      const stocksResponse = await fetch('/api/dashboard/stocks')
      if (!stocksResponse.ok) throw new Error('Failed to fetch stocks')
      const stocksData: { stocks: StockData[] } = await stocksResponse.json()

      const stocks: Stock[] = stocksData.stocks.map(stock => ({
        symbol: stock.symbol,
        name: stock.symbol,
        price: stock.fast_info.lastPrice,
        change: parseFloat(stock.stock_points_change),
        changePercent: parseFloat(stock.stocks_percentage_change)
      }))
      setPinnedStocks(stocks)
    } catch (err) {
      console.error('Failed to fetch pinned stocks:', err)
      toast.error('Failed to update pinned stocks')
    } finally {
      setLoading(false) // Set loading to false after fetching
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
      setPinnedStocks(prev => prev.filter(stock => stock.symbol !== symbol))
      toast.success(`Stock ${symbol} removed successfully`)
    } catch (error) {
      toast.error('Failed to remove stock')
    }
  }

  useEffect(() => {
    fetchPinnedStocks()
  }, [fetchPinnedStocks])

  return (
    <div>
      <Card className="shadow-md border">
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
          {loading ? (
            <div className="space-y-2">
              {Array.from({ length: 3 }).map((_, index) => (
                <div
                  key={index}
                  className="flex justify-between items-center p-4 rounded-xl border border-gray-100"
                >
                  <div className="flex-1">
                    <Skeleton className="h-5 w-24 mb-1" />
                    <Skeleton className="h-4 w-32" />
                  </div>
                  <div className="text-right mr-3">
                    <Skeleton className="h-5 w-20 mb-1" />
                    <Skeleton className="h-4 w-16" />
                  </div>
                  <Skeleton className="h-8 w-8 rounded-full" />
                </div>
              ))}
            </div>
          ) : pinnedStocks.length === 0 ? (
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
                className="flex justify-between items-center p-4 rounded-xl cursor-pointer transition-colors border border-gray-100"
              >
                <div
                  className="flex-1"
                  onClick={() => handleStockClick(stock.symbol)}
                >
                  <h4 className="font-semibold">{stock.symbol}</h4>
                  <p className="text-sm truncate">{stock.name}</p>
                </div>
                <div className="text-right mr-3">
                  <p className="font-semibold">
                    ₹{stock.price.toLocaleString('en-IN')}
                  </p>
                  <p
                    className={`text-sm font-medium ${
                      stock.change >= 0 ? 'text-green-600' : 'text-red-600'
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
      <AddStockOverlay
        isOpen={isOverlayOpen}
        onClose={() => setIsOverlayOpen(false)}
        onStockAdded={handleStockAdded}
      />
    </div>
  )
}
