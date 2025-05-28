'use client'

import { useRouter } from 'next/navigation'
import { Button } from './ui/button'
import { Input } from './ui/input'
import { useAuth } from '@/contexts/auth-context'
import Link from 'next/link'
import { useState, useEffect, useRef } from 'react'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger
} from './ui/dropdown-menu'
import { Moon, Sun, Search, Activity, Clock } from 'lucide-react'
import { useTheme } from 'next-themes'

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

interface DashboardInfo {
  market_status: string
  current_time_ist: string
}

export default function Header() {
  const router = useRouter()
  const { isLoggedIn, logout } = useAuth()
  const { setTheme } = useTheme()
  const [stockSearch, setStockSearch] = useState('')
  const [searchResults, setSearchResults] = useState<Stock[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [isDropdownOpen, setIsDropdownOpen] = useState(false)
  const [marketStatus, setMarketStatus] = useState<string>('')
  const debounceRef = useRef<NodeJS.Timeout | null>(null)

  // Get market status display info
  const getMarketStatusInfo = (status: string) => {
    const isLive =
      status.toLowerCase().includes('open') ||
      status.toLowerCase().includes('live')
    return {
      isLive,
      text: isLive ? 'Market Open' : 'Market Closed',
      color: isLive
        ? 'text-green-600 bg-green-50 border-green-200'
        : 'text-red-600 bg-red-50 border-red-200',
      icon: isLive ? Activity : Clock
    }
  }

  // Fetch market status
  useEffect(() => {
    const fetchMarketStatus = async () => {
      if (!isLoggedIn) return

      try {
        const response = await fetch('/api/dashboard/info')
        if (!response.ok) throw new Error('Failed to fetch market info')
        const data: DashboardInfo = await response.json()
        setMarketStatus(data.market_status)
      } catch (error) {
        console.error('Error fetching market status:', error)
      }
    }

    fetchMarketStatus()

    // Refresh market status every 30 seconds
    const interval = setInterval(fetchMarketStatus, 30000)
    return () => clearInterval(interval)
  }, [isLoggedIn])

  const handleLogout = () => {
    logout()
    router.push('/login')
  }

  const handleStockSearch = (e: React.FormEvent) => {
    e.preventDefault()
    if (stockSearch.trim()) {
      router.push(`/stocks/${stockSearch.trim().toUpperCase()}`)
      setSearchResults([])
      setIsDropdownOpen(false)
    }
  }

  const handleResultClick = (symbol: string) => {
    router.push(`/stocks/${symbol}`)
    setStockSearch('')
    setSearchResults([])
    setIsDropdownOpen(false)
  }

  const fetchStockResults = async (query: string) => {
    if (!query.trim()) {
      setSearchResults([])
      setIsDropdownOpen(false)
      return
    }

    setIsLoading(true)
    try {
      const response = await fetch(`api/stocks/search`, {
        method: 'POST',
        body: JSON.stringify({ input_query: query })
      })

      if (!response.ok) {
        throw new Error('Failed to fetch stock data')
      }

      const data = await response.json()
      setSearchResults(data)
      setIsDropdownOpen(true)
    } catch (error) {
      console.error('Search error:', error)
      setSearchResults([])
      setIsDropdownOpen(false)
    } finally {
      setIsLoading(false)
    }
  }

  // Debounce the search input
  useEffect(() => {
    if (debounceRef.current) {
      clearTimeout(debounceRef.current)
    }

    debounceRef.current = setTimeout(() => {
      if (isLoggedIn) {
        fetchStockResults(stockSearch)
      }
    }, 300)

    return () => {
      if (debounceRef.current) {
        clearTimeout(debounceRef.current)
      }
    }
  }, [stockSearch, isLoggedIn])

  const marketStatusInfo = getMarketStatusInfo(marketStatus)

  return (
    <header className="bg-white dark:bg-gray-900 border-b shadow-sm">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          {/* Left section - Logo and Market Status */}
          <div className="flex items-center gap-6">
            <Link href="/" className="flex items-center gap-2">
              <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-purple-600 rounded-lg flex items-center justify-center">
                <span className="text-white font-bold text-sm">Z</span>
              </div>
              <h1 className="text-xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
                ZenFi AI
              </h1>
            </Link>

            {/* Market Status Badge - Only show when logged in */}
            {isLoggedIn && marketStatus && (
              <div
                className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-sm font-medium border ${marketStatusInfo.color}`}
              >
                <marketStatusInfo.icon className="h-3.5 w-3.5" />
                {marketStatusInfo.text}
                {marketStatusInfo.isLive && (
                  <div className="w-1.5 h-1.5 bg-green-500 rounded-full animate-pulse"></div>
                )}
              </div>
            )}
          </div>

          {/* Center section - Stock Search Bar (Only show when logged in) */}
          {isLoggedIn && (
            <div className="flex-1 max-w-md mx-8 relative">
              <form onSubmit={handleStockSearch} className="relative">
                <Input
                  type="text"
                  placeholder="Search stocks (e.g., RELIANCE, TCS)"
                  value={stockSearch}
                  onChange={e => setStockSearch(e.target.value)}
                  className="pl-10 pr-4 bg-gray-50 dark:bg-gray-800 border-gray-200 dark:border-gray-700 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              </form>

              {/* Search Results Dropdown */}
              {isDropdownOpen && searchResults.length > 0 && (
                <div className="absolute z-50 w-full mt-1 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg max-h-96 overflow-y-auto">
                  {isLoading ? (
                    <div className="p-4 text-center text-muted-foreground">
                      <div className="animate-spin rounded-full h-4 w-4 border-2 border-blue-500 border-t-transparent mx-auto"></div>
                    </div>
                  ) : (
                    searchResults.map(stock => (
                      <div
                        key={stock.symbol}
                        className="p-3 hover:bg-gray-50 dark:hover:bg-gray-700 cursor-pointer border-b border-gray-100 dark:border-gray-700 last:border-b-0"
                        onClick={() => handleResultClick(stock.symbol)}
                      >
                        <div className="flex justify-between items-start">
                          <span className="font-semibold text-gray-900 dark:text-white">
                            {stock.symbol}
                          </span>
                          <span className="text-sm text-gray-500 dark:text-gray-400 bg-gray-100 dark:bg-gray-600 px-2 py-0.5 rounded">
                            {stock.exchDisp}
                          </span>
                        </div>
                        <div className="text-sm text-gray-600 dark:text-gray-300 mt-1">
                          {stock.longname}
                        </div>
                        {stock.sector && stock.industry && (
                          <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                            {stock.sector} • {stock.industry}
                          </div>
                        )}
                      </div>
                    ))
                  )}
                </div>
              )}
            </div>
          )}

          {/* Right section - Navigation and Theme */}
          <div className="flex items-center gap-2">
            {/* Theme Toggle */}
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  className="hover:bg-gray-100 dark:hover:bg-gray-800"
                >
                  <Sun className="h-[1.2rem] w-[1.2rem] rotate-0 scale-100 transition-all dark:-rotate-90 dark:scale-0" />
                  <Moon className="absolute h-[1.2rem] w-[1.2rem] rotate-90 scale-0 transition-all dark:rotate-0 dark:scale-100" />
                  <span className="sr-only">Toggle theme</span>
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuItem onClick={() => setTheme('light')}>
                  Light
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => setTheme('dark')}>
                  Dark
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => setTheme('system')}>
                  System
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>

            {/* Navigation Menu */}
            {isLoggedIn ? (
              <>
                <Button
                  variant="ghost"
                  onClick={() => router.push('/')}
                  className="hover:bg-gray-100 dark:hover:bg-gray-800"
                >
                  Home
                </Button>
                <Button
                  variant="ghost"
                  onClick={() => router.push('/portfolio')}
                  className="hover:bg-gray-100 dark:hover:bg-gray-800"
                >
                  Portfolio
                </Button>
                <Button
                  variant="ghost"
                  onClick={() => router.push('/news')}
                  className="hover:bg-gray-100 dark:hover:bg-gray-800"
                >
                  News
                </Button>

                {/* More Menu for additional items */}
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button
                      variant="ghost"
                      className="hover:bg-gray-100 dark:hover:bg-gray-800"
                    >
                      More
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end">
                    <DropdownMenuItem
                      onClick={() => router.push('/knowledge_base')}
                    >
                      Knowledge Base
                    </DropdownMenuItem>
                    <DropdownMenuItem onClick={() => router.push('/sessions')}>
                      Chat History
                    </DropdownMenuItem>
                    <DropdownMenuItem onClick={() => router.push('/settings')}>
                      Settings
                    </DropdownMenuItem>
                    <DropdownMenuItem
                      onClick={handleLogout}
                      className="text-red-600"
                    >
                      Logout
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              </>
            ) : (
              <>
                <Button
                  variant="ghost"
                  onClick={() => router.push('/login')}
                  className="hover:bg-gray-100 dark:hover:bg-gray-800"
                >
                  Login
                </Button>
                <Button
                  variant="default"
                  onClick={() => router.push('/register')}
                  className="bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700"
                >
                  Register
                </Button>
              </>
            )}
          </div>
        </div>
      </div>
    </header>
  )
}
