'use client'

import { useState, useEffect, useRef } from 'react'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Search } from 'lucide-react'
import { toast } from 'sonner'

interface Stock {
  exchange: string
  shortname: string
  quoteType: string
  symbol: string
  longname: string
  exchDisp: string
  sector?: string
  industry?: string
}

interface AddStockOverlayProps {
  isOpen: boolean
  onClose: () => void
  onStockAdded: () => void
}

export default function AddStockOverlay({
  isOpen,
  onClose,
  onStockAdded
}: AddStockOverlayProps) {
  const [searchQuery, setSearchQuery] = useState('')
  const [searchResults, setSearchResults] = useState<Stock[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const debounceRef = useRef<NodeJS.Timeout | null>(null)

  const fetchStockResults = async (query: string) => {
    if (!query.trim()) {
      setSearchResults([])
      return
    }

    setIsLoading(true)
    try {
      const response = await fetch('/api/stocks/search', {
        method: 'POST',
        body: JSON.stringify({ input_query: query })
      })

      if (!response.ok) {
        throw new Error('Failed to fetch stock data')
      }

      const data = await response.json()
      setSearchResults(data)
    } catch (error) {
      console.error('Search error:', error)
      setSearchResults([])
      toast.error('Failed to load stock results')
    } finally {
      setIsLoading(false)
    }
  }

  const handleAddStock = async (stock: Stock) => {
    try {
      const response = await fetch('/api/dashboard/stocks/add', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ symbol: stock.symbol })
      })

      if (!response.ok) {
        throw new Error('Failed to add stock')
      }

      toast.success(`${stock.symbol} added to pinned stocks`)
      setSearchQuery('')
      setSearchResults([])
      onStockAdded()
      onClose()
    } catch (error) {
      console.error('Add stock error:', error)
      toast.error('Failed to add stock')
    }
  }

  useEffect(() => {
    if (debounceRef.current) {
      clearTimeout(debounceRef.current)
    }

    debounceRef.current = setTimeout(() => {
      fetchStockResults(searchQuery)
    }, 300)

    return () => {
      if (debounceRef.current) {
        clearTimeout(debounceRef.current)
      }
    }
  }, [searchQuery])

  useEffect(() => {
    if (!isOpen) {
      setSearchQuery('')
      setSearchResults([])
      setIsLoading(false)
    }
  }, [isOpen])

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Add Pinned Stock</DialogTitle>
        </DialogHeader>
        <div className="relative mt-4">
          <Input
            type="text"
            placeholder="Search stocks (e.g., RELIANCE, NVIDIA)"
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
            className="pl-10 pr-4"
          />
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
        </div>
        <div className="mt-4 max-h-64 overflow-y-auto">
          {isLoading ? (
            <div className="p-4 text-center text-muted-foreground">
              Loading...
            </div>
          ) : searchResults.length === 0 && searchQuery.trim() ? (
            <div className="p-4 text-center text-muted-foreground">
              No results found
            </div>
          ) : (
            searchResults.map(stock => (
              <div
                key={stock.symbol}
                className="flex justify-between items-center p-3 rounded-lg hover:bg-muted cursor-pointer transition-colors"
                onClick={() => handleAddStock(stock)}
              >
                <div>
                  <h4 className="font-medium">{stock.symbol}</h4>
                  <p className="text-sm text-muted-foreground truncate">
                    {stock.longname}
                  </p>
                </div>
                <div className="text-sm text-muted-foreground">
                  {stock.exchDisp}
                </div>
              </div>
            ))
          )}
        </div>
      </DialogContent>
    </Dialog>
  )
}
