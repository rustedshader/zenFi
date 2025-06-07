'use client'

import { useParams, useRouter } from 'next/navigation'
import { useEffect, useState, useRef } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow
} from '@/components/ui/table'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger
} from '@/components/ui/dialog'
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger
} from '@/components/ui/collapsible'
import { toast } from 'sonner'
import {
  ArrowUp,
  ArrowDown,
  ChevronLeft,
  Plus,
  Trash2,
  TrendingUp,
  TrendingDown,
  Search,
  ChevronDown,
  ChevronRight,
  Calendar,
  Star
} from 'lucide-react'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue
} from '@/components/ui/select'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

interface Portfolio {
  id: string
  name: string
  total_value_inr: number
  total_day_gain_inr: number
  total_gain_inr: number
  assets: Asset[]
  ai_summary?: string
  is_default: boolean
}

interface Asset {
  identifier: string
  asset_type: string
  quantity: number
  purchase_price: number
  value_base: number
  day_gain_base: number
  total_gain_base: number
  day_gain_percent: number
  total_gain_percent: number
  purchase_date?: string
  news: NewsItem[]
}

interface NewsItem {
  title: string
  summary: string
  pubDate: string
  url: string
}

interface NewAsset {
  asset_type: string
  identifier: string
  quantity: string
  purchase_price: string
  purchase_date: string
}

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

interface CombinedAsset extends Asset {
  totalQuantity: number
  averagePurchasePrice: number
  positions: Asset[]
}

export default function PortfolioDetails() {
  const params = useParams()
  const router = useRouter()
  const [portfolio, setPortfolio] = useState<Portfolio | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedAsset, setSelectedAsset] = useState<Asset | null>(null)
  const [isAddAssetOpen, setIsAddAssetOpen] = useState(false)
  const [newAsset, setNewAsset] = useState<NewAsset>({
    asset_type: 'Stock',
    identifier: '',
    quantity: '',
    purchase_price: '',
    purchase_date: new Date().toISOString().split('T')[0]
  })
  const [assetToDelete, setAssetToDelete] = useState<Asset | null>(null)

  // Stock search states
  const [stockSearch, setStockSearch] = useState('')
  const [searchResults, setSearchResults] = useState<Stock[]>([])
  const [isSearchLoading, setIsSearchLoading] = useState(false)
  const [isSearchDropdownOpen, setIsSearchDropdownOpen] = useState(false)
  const debounceRef = useRef<NodeJS.Timeout | null>(null)

  const portfolioId = params.id as string

  useEffect(() => {
    const fetchPortfolio = async () => {
      setIsLoading(true)
      try {
        // Fetch portfolio details
        const portfolioResponse = await fetch(`/api/portfolio/info`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ portfolio_id: portfolioId })
        })
        if (!portfolioResponse.ok) throw new Error('Failed to fetch portfolio')
        const portfolioData = await portfolioResponse.json()

        // Fetch default status
        const defaultStatusResponse = await fetch(
          `/api/portfolio/default_status`,
          {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ portfolio_id: portfolioId })
          }
        )
        if (!defaultStatusResponse.ok)
          throw new Error('Failed to fetch default status')
        const defaultStatusData = await defaultStatusResponse.json()

        // Combine portfolio data with default status
        setPortfolio({
          ...portfolioData,
          is_default: defaultStatusData.is_default
        })
      } catch (err) {
        setError('Failed to load portfolio. Please try again.')
        toast.error('Failed to load portfolio')
      } finally {
        setIsLoading(false)
      }
    }
    fetchPortfolio()
  }, [portfolioId])

  // Stock search functionality
  const fetchStockResults = async (query: string) => {
    if (!query.trim()) {
      setSearchResults([])
      setIsSearchDropdownOpen(false)
      return
    }

    setIsSearchLoading(true)
    try {
      const response = await fetch(`/api/stocks/search`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ input_query: query })
      })

      if (!response.ok) {
        throw new Error('Failed to fetch stock data')
      }

      const data = await response.json()
      setSearchResults(data)
      setIsSearchDropdownOpen(true)
    } catch (error) {
      console.error('Search error:', error)
      setSearchResults([])
      setIsSearchDropdownOpen(false)
    } finally {
      setIsSearchLoading(false)
    }
  }

  // Debounce the search input
  useEffect(() => {
    if (debounceRef.current) {
      clearTimeout(debounceRef.current)
    }

    debounceRef.current = setTimeout(() => {
      fetchStockResults(stockSearch)
    }, 300)

    return () => {
      if (debounceRef.current) {
        clearTimeout(debounceRef.current)
      }
    }
  }, [stockSearch])

  const handleStockSelect = (stock: Stock) => {
    setNewAsset({ ...newAsset, identifier: stock.symbol })
    setStockSearch(stock.symbol)
    setSearchResults([])
    setIsSearchDropdownOpen(false)
  }

  // Handle toggling portfolio default status
  const handleDefaultToggle = async (setDefault: boolean) => {
    try {
      const response = await fetch('/api/portfolio/default', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          portfolio_id: portfolioId,
          set_default: setDefault
        })
      })
      if (!response.ok) {
        throw new Error(
          `Failed to ${setDefault ? 'set' : 'remove'} default portfolio`
        )
      }
      setPortfolio(prev => (prev ? { ...prev, is_default: setDefault } : prev))
      toast.success(`Portfolio ${setDefault ? 'set as' : 'removed as'} default`)
    } catch (error) {
      console.error(error)
      toast.error(
        `Failed to ${setDefault ? 'set' : 'remove'} default portfolio`
      )
    }
  }

  // Combine duplicate assets
  const combineAssets = (assets: Asset[]): CombinedAsset[] => {
    const grouped = assets.reduce((acc, asset) => {
      const key = asset.identifier
      if (!acc[key]) {
        acc[key] = []
      }
      acc[key].push(asset)
      return acc
    }, {} as Record<string, Asset[]>)

    return Object.entries(grouped).map(([identifier, positions]) => {
      if (positions.length === 1) {
        return {
          ...positions[0],
          totalQuantity: positions[0].quantity,
          averagePurchasePrice: positions[0].purchase_price,
          positions: positions
        }
      }

      // Calculate combined values for multiple positions
      const totalQuantity = positions.reduce(
        (sum, pos) => sum + pos.quantity,
        0
      )
      const totalInvestment = positions.reduce(
        (sum, pos) => sum + pos.quantity * pos.purchase_price,
        0
      )
      const averagePurchasePrice = totalInvestment / totalQuantity
      const totalCurrentValue = positions.reduce(
        (sum, pos) => sum + pos.value_base,
        0
      )
      const totalDayGain = positions.reduce(
        (sum, pos) => sum + pos.day_gain_base,
        0
      )
      const totalGain = totalCurrentValue - totalInvestment

      return {
        identifier,
        asset_type: positions[0].asset_type,
        quantity: totalQuantity,
        purchase_price: averagePurchasePrice,
        value_base: totalCurrentValue,
        day_gain_base: totalDayGain,
        total_gain_base: totalGain,
        day_gain_percent:
          (totalDayGain / (totalCurrentValue - totalDayGain)) * 100,
        total_gain_percent: (totalGain / totalInvestment) * 100,
        news: positions[0].news || [],
        totalQuantity,
        averagePurchasePrice,
        positions
      }
    })
  }

  const formatCurrency = (value: number | null | undefined) => {
    if (value === null || value === undefined) return 'N/A'
    return `₹${value.toLocaleString('en-IN', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    })}`
  }

  const formatPercentage = (value: number | null | undefined) => {
    if (value === null || value === undefined) return 'N/A'
    return `${value.toFixed(2)}%`
  }

  const handleAddAsset = async () => {
    if (
      !newAsset.identifier.trim() ||
      !newAsset.quantity ||
      !newAsset.purchase_price
    ) {
      toast.error('Please fill in all required fields')
      return
    }

    const assetData = {
      portfolio_id: portfolioId,
      asset_type: newAsset.asset_type,
      identifier: newAsset.identifier,
      quantity: parseFloat(newAsset.quantity),
      purchase_price: parseFloat(newAsset.purchase_price),
      purchase_date: newAsset.purchase_date,
      notes: null
    }

    try {
      const response = await fetch(`/api/portfolio/add_asset`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(assetData)
      })
      if (!response.ok) throw new Error('Failed to add asset')

      // Fetch updated portfolio with portfolio_id
      const updatedPortfolioResponse = await fetch(`/api/portfolio/info`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ portfolio_id: portfolioId })
      })
      if (!updatedPortfolioResponse.ok)
        throw new Error('Failed to fetch updated portfolio')
      const updatedPortfolio = await updatedPortfolioResponse.json()

      setPortfolio(updatedPortfolio)
      setIsAddAssetOpen(false)
      setNewAsset({
        asset_type: 'Stock',
        identifier: '',
        quantity: '',
        purchase_price: '',
        purchase_date: new Date().toISOString().split('T')[0]
      })
      setStockSearch('')
      toast.success('Asset added successfully')
    } catch (error) {
      console.error(error)
      toast.error('Failed to add asset')
    }
  }

  const handleDeleteAsset = async () => {
    if (!assetToDelete) return
    try {
      const response = await fetch(
        `/api/portfolio/${portfolioId}/assets/${assetToDelete.identifier}`,
        {
          method: 'DELETE'
        }
      )
      if (!response.ok) throw new Error('Failed to delete asset')

      // Fetch updated portfolio with portfolio_id
      const updatedPortfolioResponse = await fetch(`/api/portfolio/info`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ portfolio_id: portfolioId })
      })
      if (!updatedPortfolioResponse.ok)
        throw new Error('Failed to fetch updated portfolio')
      const updatedPortfolio = await updatedPortfolioResponse.json()

      setPortfolio(updatedPortfolio)
      setAssetToDelete(null)
      toast.success('Asset deleted successfully')
    } catch (error) {
      console.error(error)
      toast.error('Failed to delete asset')
    }
  }

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    )
  }

  if (error || !portfolio) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center space-y-4">
          <h1 className="text-2xl font-bold text-red-600">Error</h1>
          <p className="text-gray-600">{error || 'Portfolio not found'}</p>
          <Button onClick={() => router.back()} variant="outline">
            <ChevronLeft className="h-4 w-4 mr-2" />
            Go Back
          </Button>
        </div>
      </div>
    )
  }

  const combinedAssets = combineAssets(portfolio.assets)

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <div className="bg-card sticky">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <Button variant="ghost" size="sm" onClick={() => router.back()}>
                <ChevronLeft className="h-4 w-4 mr-1" />
                Back
              </Button>
              <div>
                <h1 className="text-2xl font-bold">{portfolio.name}</h1>
                <p className="text-sm text-muted-foreground">
                  Portfolio ID: {portfolio.id}
                </p>
              </div>
            </div>
            <div className="flex space-x-2">
              <Button
                variant={portfolio.is_default ? 'outline' : 'default'}
                onClick={() => handleDefaultToggle(!portfolio.is_default)}
              >
                <Star className="h-4 w-4 mr-2" />
                {portfolio.is_default ? 'Remove Default' : 'Set as Default'}
              </Button>
              <Button onClick={() => setIsAddAssetOpen(true)}>
                <Plus className="h-4 w-4 mr-2" />
                Add Asset
              </Button>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Portfolio Summary */}
        <Card className="mb-8">
          <CardHeader>
            <CardTitle>Portfolio Summary</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div className="text-center p-6 rounded-lg border">
                <p className="text-sm text-muted-foreground mb-2">
                  Total Portfolio Value
                </p>
                <p className="text-3xl font-bold ">
                  {formatCurrency(portfolio.total_value_inr)}
                </p>
              </div>
              <div className="text-center p-6 rounded-lg border">
                <p className="text-sm text-muted-foreground mb-2">
                  Today's Gain/Loss
                </p>
                <p
                  className={`text-2xl font-semibold flex items-center justify-center ${
                    portfolio.total_day_gain_inr >= 0
                      ? 'text-green-600'
                      : 'text-red-600'
                  }`}
                >
                  {formatCurrency(portfolio.total_day_gain_inr)}
                  {portfolio.total_day_gain_inr >= 0 ? (
                    <TrendingUp className="h-5 w-5 ml-2" />
                  ) : (
                    <TrendingDown className="h-5 w-5 ml-2" />
                  )}
                </p>
              </div>
              <div className="text-center p-6 rounded-lg border">
                <p className="text-sm text-muted-foreground mb-2">
                  Total Gain/Loss
                </p>
                <p
                  className={`text-2xl font-semibold flex items-center justify-center ${
                    portfolio.total_gain_inr >= 0
                      ? 'text-green-600'
                      : 'text-red-600'
                  }`}
                >
                  {formatCurrency(portfolio.total_gain_inr)}
                  {portfolio.total_gain_inr >= 0 ? (
                    <ArrowUp className="h-5 w-5 ml-2" />
                  ) : (
                    <ArrowDown className="h-5 w-5 ml-2" />
                  )}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>
              Holdings ({combinedAssets.length} unique assets)
            </CardTitle>
          </CardHeader>
          <CardContent>
            {combinedAssets.length === 0 ? (
              <p className="text-muted-foreground text-center py-8">
                No assets in this portfolio yet.
              </p>
            ) : (
              <div className="space-y-4">
                {combinedAssets.map(asset => (
                  <Collapsible
                    key={asset.identifier}
                    className="border rounded-lg"
                  >
                    <div className="p-4">
                      <div className="grid grid-cols-8 gap-4 items-center">
                        <div className="col-span-2">
                          <div className="font-medium">{asset.identifier}</div>
                          <div className="text-sm text-muted-foreground">
                            {asset.asset_type}
                          </div>
                        </div>
                        <div className="text-right">
                          <div className="font-medium">
                            {asset.quantity?.toLocaleString() || 'N/A'}
                          </div>
                          <div className="text-sm text-muted-foreground">
                            Shares
                          </div>
                        </div>
                        <div className="text-right">
                          <div className="font-medium">
                            {formatCurrency(asset.purchase_price)}
                          </div>
                          <div className="text-sm text-muted-foreground">
                            Avg Price
                          </div>
                        </div>
                        <div className="text-right">
                          <div className="font-semibold">
                            {formatCurrency(asset.value_base)}
                          </div>
                          <div className="text-sm text-muted-foreground">
                            Current Value
                          </div>
                        </div>
                        <div
                          className={`text-right ${
                            asset.day_gain_base >= 0
                              ? 'text-green-600'
                              : 'text-red-600'
                          }`}
                        >
                          <div className="font-medium">
                            {formatCurrency(asset.day_gain_base)}
                          </div>
                          <div className="text-sm">
                            ({formatPercentage(asset.day_gain_percent)})
                          </div>
                        </div>
                        <div
                          className={`text-right ${
                            asset.total_gain_base >= 0
                              ? 'text-green-600'
                              : 'text-red-600'
                          }`}
                        >
                          <div className="font-medium">
                            {formatCurrency(asset.total_gain_base)}
                          </div>
                          <div className="text-sm">
                            ({formatPercentage(asset.total_gain_percent)})
                          </div>
                        </div>
                        <div className="flex items-center justify-end gap-1 sm:gap-2">
                          {asset.positions && asset.positions.length > 1 && (
                            <CollapsibleTrigger asChild>
                              <Button
                                variant="outline"
                                size="sm"
                                className="whitespace-nowrap"
                              >
                                <ChevronDown className="h-4 w-4 sm:mr-1" />
                                <span className="hidden sm:inline">
                                  {asset.positions.length} lots
                                </span>
                                <span className="sm:hidden">
                                  {asset.positions.length}
                                </span>
                              </Button>
                            </CollapsibleTrigger>
                          )}
                          {asset.news && asset.news.length > 0 && (
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => setSelectedAsset(asset)}
                            >
                              News
                            </Button>
                          )}
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => setAssetToDelete(asset)}
                            className="text-red-600 hover:text-red-700"
                            aria-label="Delete asset"
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </div>
                      </div>
                    </div>
                    {asset.positions && asset.positions.length > 1 && (
                      <CollapsibleContent className="px-4 pb-4 pt-0">
                        <div className="border-t pt-4 space-y-2">
                          {asset.positions.map((position, posIndex) => (
                            <div
                              key={`${asset.identifier}-pos-${posIndex}`}
                              className="grid grid-cols-8 gap-4 items-center text-sm py-2 bg-muted/50 rounded px-2 sm:pl-4"
                            >
                              <div className="col-span-2 flex items-center">
                                <Calendar className="h-3 w-3 mr-1 flex-shrink-0" />
                                <span className="truncate">
                                  {position.purchase_date
                                    ? new Date(
                                        position.purchase_date
                                      ).toLocaleDateString(undefined, {
                                        year: 'numeric',
                                        month: 'short',
                                        day: 'numeric'
                                      })
                                    : 'N/A'}
                                </span>
                              </div>
                              <div className="text-right">
                                {position.quantity?.toLocaleString() || 'N/A'}
                              </div>
                              <div className="text-right">
                                {formatCurrency(position.purchase_price)}
                              </div>
                              <div className="text-right">
                                {formatCurrency(position.value_base)}
                              </div>
                              <div
                                className={`text-right ${
                                  position.day_gain_base >= 0
                                    ? 'text-green-600'
                                    : 'text-red-600'
                                }`}
                              >
                                {formatCurrency(position.day_gain_base)}
                              </div>
                              <div
                                className={`text-right ${
                                  position.total_gain_base >= 0
                                    ? 'text-green-600'
                                    : 'text-red-600'
                                }`}
                              >
                                {formatCurrency(position.total_gain_base)}
                              </div>
                              <div></div>
                            </div>
                          ))}
                        </div>
                      </CollapsibleContent>
                    )}
                  </Collapsible>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {selectedAsset && (
          <Dialog
            open={!!selectedAsset}
            onOpenChange={isOpen => {
              if (!isOpen) setSelectedAsset(null)
            }}
          >
            <DialogContent className="max-w-4xl max-h-[80vh] overflow-y-auto">
              <DialogHeader>
                <DialogTitle>
                  {selectedAsset.identifier} - Latest News & Updates
                </DialogTitle>
              </DialogHeader>
              <div className="space-y-6 py-4">
                <Card>
                  <CardHeader>
                    <CardTitle>Asset Overview</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                      <div>
                        <p className="text-sm text-muted-foreground">
                          Current Value
                        </p>
                        <p className="text-lg font-semibold">
                          {formatCurrency(selectedAsset.value_base)}
                        </p>
                      </div>
                      <div>
                        <p className="text-sm text-muted-foreground">
                          Day Gain/Loss
                        </p>
                        <p
                          className={`text-lg font-semibold ${
                            selectedAsset.day_gain_base >= 0
                              ? 'text-green-600'
                              : 'text-red-600'
                          }`}
                        >
                          {formatCurrency(selectedAsset.day_gain_base)}
                        </p>
                      </div>
                      <div>
                        <p className="text-sm text-muted-foreground">
                          Total Gain/Loss
                        </p>
                        <p
                          className={`text-lg font-semibold ${
                            selectedAsset.total_gain_base >= 0
                              ? 'text-green-600'
                              : 'text-red-600'
                          }`}
                        >
                          {formatCurrency(selectedAsset.total_gain_base)}
                        </p>
                      </div>
                      <div>
                        <p className="text-sm text-muted-foreground">
                          Total Return %
                        </p>
                        <p
                          className={`text-lg font-semibold ${
                            selectedAsset.total_gain_percent >= 0
                              ? 'text-green-600'
                              : 'text-red-600'
                          }`}
                        >
                          {formatPercentage(selectedAsset.total_gain_percent)}
                        </p>
                      </div>
                    </div>
                  </CardContent>
                </Card>
                {selectedAsset.news && selectedAsset.news.length > 0 && (
                  <Card>
                    <CardHeader>
                      <CardTitle>Latest News</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="space-y-4">
                        {selectedAsset.news
                          .slice(0, 5)
                          .map((newsItem, index) => (
                            <div
                              key={newsItem.url || index}
                              className="border-l-4 border-primary pl-4 py-2"
                            >
                              <h4 className="font-semibold mb-1">
                                {newsItem.title}
                              </h4>
                              {newsItem.summary && (
                                <p className="text-sm text-muted-foreground mb-2">
                                  {newsItem.summary}
                                </p>
                              )}
                              <div className="flex justify-between items-center">
                                <span className="text-xs text-muted-foreground">
                                  {newsItem.pubDate
                                    ? new Date(
                                        newsItem.pubDate
                                      ).toLocaleDateString(undefined, {
                                        year: 'numeric',
                                        month: 'short',
                                        day: 'numeric'
                                      })
                                    : 'N/A'}
                                </span>
                                <Button
                                  variant="outline"
                                  size="sm"
                                  onClick={() =>
                                    window.open(
                                      newsItem.url,
                                      '_blank',
                                      'noopener noreferrer'
                                    )
                                  }
                                >
                                  Read More
                                </Button>
                              </div>
                            </div>
                          ))}
                      </div>
                    </CardContent>
                  </Card>
                )}
              </div>
            </DialogContent>
          </Dialog>
        )}

        <Dialog open={isAddAssetOpen} onOpenChange={setIsAddAssetOpen}>
          <DialogContent className="max-w-md">
            <DialogHeader>
              <DialogTitle>Add New Asset</DialogTitle>
            </DialogHeader>
            <div className="space-y-4">
              <div>
                <Label htmlFor="asset_type">Asset Type</Label>
                <Select
                  value={newAsset.asset_type}
                  onValueChange={value =>
                    setNewAsset({ ...newAsset, asset_type: value })
                  }
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select asset type" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="Stock">Stock</SelectItem>
                    <SelectItem value="Bond">Bond</SelectItem>
                    <SelectItem value="Other">Other</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div>
                <Label htmlFor="identifier">Stock Symbol</Label>
                <div className="relative">
                  <Input
                    id="identifier"
                    value={stockSearch}
                    onChange={e => setStockSearch(e.target.value)}
                    placeholder="Search stocks (e.g., RELIANCE, NVIDIA)"
                    className="pl-10"
                  />
                  <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                  {isSearchDropdownOpen && searchResults.length > 0 && (
                    <Card className="absolute z-50 w-full mt-1 border rounded-md shadow-lg max-h-60 overflow-y-auto">
                      {isSearchLoading ? (
                        <div className="p-4 text-center">
                          <div className="animate-spin rounded-full h-4 w-4 border-2 border-primary border-t-transparent mx-auto"></div>
                        </div>
                      ) : (
                        searchResults.map(stock => (
                          <div
                            key={stock.symbol}
                            className="p-3 hover:bg-accent cursor-pointer border-b last:border-b-0"
                            onClick={() => handleStockSelect(stock)}
                          >
                            <div className="flex justify-between items-start">
                              <span className="font-semibold">
                                {stock.symbol}
                              </span>
                              <span className="text-xs bg-secondary px-2 py-1 rounded">
                                {stock.exchDisp}
                              </span>
                            </div>
                            <div className="text-sm text-muted-foreground mt-1">
                              {stock.longname}
                            </div>
                            {stock.sector && stock.industry && (
                              <div className="text-xs text-muted-foreground mt-1">
                                {stock.sector} • {stock.industry}
                              </div>
                            )}
                          </div>
                        ))
                      )}
                    </Card>
                  )}
                </div>
              </div>

              <div>
                <Label htmlFor="quantity">Quantity</Label>
                <Input
                  id="quantity"
                  type="number"
                  value={newAsset.quantity}
                  onChange={e =>
                    setNewAsset({ ...newAsset, quantity: e.target.value })
                  }
                  placeholder="e.g., 10"
                />
              </div>

              <div>
                <Label htmlFor="purchase_price">Purchase Price (₹)</Label>
                <Input
                  id="purchase_price"
                  type="number"
                  step="0.01"
                  value={newAsset.purchase_price}
                  onChange={e =>
                    setNewAsset({ ...newAsset, purchase_price: e.target.value })
                  }
                  placeholder="e.g., 2500.00"
                />
              </div>

              <div>
                <Label htmlFor="purchase_date">Purchase Date</Label>
                <Input
                  id="purchase_date"
                  type="date"
                  value={newAsset.purchase_date}
                  onChange={e =>
                    setNewAsset({ ...newAsset, purchase_date: e.target.value })
                  }
                />
              </div>
            </div>
            <div className="mt-6 flex justify-end space-x-2">
              <Button
                variant="outline"
                onClick={() => {
                  setIsAddAssetOpen(false)
                  setStockSearch('')
                  setSearchResults([])
                  setIsSearchDropdownOpen(false)
                }}
              >
                Cancel
              </Button>
              <Button onClick={handleAddAsset}>Add Asset</Button>
            </div>
          </DialogContent>
        </Dialog>

        <Dialog
          open={!!assetToDelete}
          onOpenChange={() => setAssetToDelete(null)}
        >
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Confirm Deletion</DialogTitle>
            </DialogHeader>
            <p>
              Are you sure you want to delete{' '}
              <strong>{assetToDelete?.identifier}</strong> from your portfolio?
            </p>
            <div className="flex justify-end space-x-2 mt-6">
              <Button variant="outline" onClick={() => setAssetToDelete(null)}>
                Cancel
              </Button>
              <Button variant="destructive" onClick={handleDeleteAsset}>
                Delete Asset
              </Button>
            </div>
          </DialogContent>
        </Dialog>

        {portfolio.ai_summary && (
          <Card className="mb-8">
            <CardHeader>
              <CardTitle className="flex items-center">
                <span className="bg-gradient-to-r from-purple-600 to-blue-600 bg-clip-text text-transparent">
                  AI Portfolio Insights
                </span>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="prose prose-sm max-w-none dark:prose-invert min-h-[100px]">
                {portfolio.ai_summary ? (
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>
                    {portfolio.ai_summary}
                  </ReactMarkdown>
                ) : (
                  <p className="text-muted-foreground">
                    No AI insights available.
                  </p>
                )}
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  )
}
