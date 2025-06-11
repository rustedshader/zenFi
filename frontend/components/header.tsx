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
import { Moon, Sun, Search, Activity, Clock, MessageCircle } from 'lucide-react'
import { useTheme } from 'next-themes'
import Image from 'next/image'
import ZenfiLogo from '@/public/zenfi_logo.png'

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

  const getMarketStatusInfo = (status: string) => {
    const isLive = status.toLowerCase().includes('active')
    return {
      isLive,
      text: isLive ? 'Market Open' : 'Market Closed',
      color: isLive ? 'text-green-600' : 'text-red-600 ',
      icon: isLive ? Activity : Clock
    }
  }

  useEffect(() => {
    const fetchMarketStatus = async () => {
      try {
        const response = await fetch('/api/dashboard/market_status', {
          credentials: 'include'
        })
        if (!response.ok) throw new Error('Failed to fetch market info')
        const data: DashboardInfo = await response.json()
        setMarketStatus(data.market_status)
      } catch (error) {
        console.error('Error fetching market status:', error)
        setMarketStatus('')
      }
    }

    if (isLoggedIn) {
      fetchMarketStatus()
      const intervalId = setInterval(fetchMarketStatus, 300000)
      return () => clearInterval(intervalId)
    } else {
      setMarketStatus('')
    }
  }, [isLoggedIn])

  const handleLogout = () => {
    logout()
    router.push(`/login`)
  }

  const handleStockSearch = (e: React.FormEvent) => {
    e.preventDefault()
    if (stockSearch.trim()) {
      router.push(`/stocks/${stockSearch.trim().toUpperCase()}`)
      setStockSearch('')
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
    if (!query.trim() || !isLoggedIn) {
      setSearchResults([])
      setIsDropdownOpen(false)
      return
    }

    setIsLoading(true)
    try {
      const response = await fetch(`/api/stocks/search`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ input_query: query }),
        credentials: 'include'
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

  const handleNewChat = async () => {
    try {
      const response = await fetch('/api/sessions/init', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: 'Start a new chat',
          isDeepResearch: false
        })
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.error || 'Failed to create session')
      }

      const data = await response.json()
      router.push(
        `/chat/${data.session_id}?query=${encodeURIComponent(
          'Start a new chat'
        )}&isDeepResearch=false`
      )
    } catch (error) {
      console.error('Error creating new chat session:', error)
      router.push('/')
    }
  }

  const marketStatusInfo = getMarketStatusInfo(marketStatus)

  return (
    <header className="border-b shadow-sm">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          <div className="flex items-center gap-6">
            <Link href="/" className="flex items-center gap-3">
              <span className="relative h-10 w-10">
                <Image
                  src={ZenfiLogo}
                  alt="zenfi_logo"
                  fill
                  priority
                  className="object-contain"
                />
              </span>
              <h1 className="text-xl font-bold">ZenFi AI</h1>
            </Link>

            {isLoggedIn && marketStatus && (
              <div
                className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-2xl text-sm font-medium border ${marketStatusInfo.color}`}
              >
                <marketStatusInfo.icon className="h-3.5 w-3.5" />
                {marketStatusInfo.text}
                {marketStatusInfo.isLive && (
                  <div className="w-1.5 h-1.5 bg-green-500 rounded-full animate-pulse"></div>
                )}
              </div>
            )}
          </div>

          {isLoggedIn && (
            <div className="flex-1 max-w-md mx-8 relative">
              <form onSubmit={handleStockSearch} className="relative">
                <Input
                  type="text"
                  placeholder="Search stocks (e.g., RELIANCE, NVIDIA)"
                  value={stockSearch}
                  onChange={e => setStockSearch(e.target.value)}
                  className="pl-10 pr-4"
                />
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              </form>

              {isDropdownOpen && (
                <div className="absolute z-50 w-full mt-1 bg-background border rounded-lg shadow-lg max-h-96 overflow-y-auto">
                  {isLoading ? (
                    <div className="p-4 text-center text-muted-foreground">
                      <div className="animate-spin rounded-full h-4 w-4 border-2 border-primary border-t-transparent mx-auto"></div>
                    </div>
                  ) : searchResults.length > 0 ? (
                    searchResults.map(stock => (
                      <div
                        key={stock.symbol}
                        className="p-3 cursor-pointer hover:bg-muted border-b last:border-b-0"
                        onClick={() => handleResultClick(stock.symbol)}
                      >
                        <div className="flex justify-between items-start">
                          <span className="font-semibold">{stock.symbol}</span>
                          <span className="text-sm px-2 py-0.5 rounded bg-muted text-muted-foreground">
                            {stock.exchDisp}
                          </span>
                        </div>
                        <div className="text-sm mt-1">{stock.longname}</div>
                        {stock.sector && stock.industry && (
                          <div className="text-xs text-muted-foreground mt-1">
                            {stock.sector} • {stock.industry}
                          </div>
                        )}
                      </div>
                    ))
                  ) : (
                    <div className="p-4 text-center text-sm text-muted-foreground">
                      No results found.
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          <div className="flex items-center gap-2">
            {isLoggedIn ? (
              <>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={handleNewChat}
                  title="New Chat"
                >
                  <MessageCircle className="h-4 w-4" />
                </Button>
                <Button
                  variant="ghost"
                  onClick={() => router.push('/watchlist')}
                >
                  Watchlist
                </Button>
                <Button
                  variant="ghost"
                  onClick={() => router.push('/portfolio')}
                >
                  Portfolio
                </Button>
                <Button
                  variant="ghost"
                  onClick={() => router.push('/knowledge_base')}
                >
                  Finance Knowledge Base
                </Button>
                <Button variant="ghost" onClick={() => router.push('/news')}>
                  News
                </Button>
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button variant="ghost">More</Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end">
                    <DropdownMenuItem onClick={() => router.push('/sessions')}>
                      Chat History
                    </DropdownMenuItem>
                    <DropdownMenuItem onClick={() => router.push('/settings')}>
                      Settings
                    </DropdownMenuItem>
                    <DropdownMenuItem
                      onClick={handleLogout}
                      className="text-red-600 focus:text-red-500"
                    >
                      Logout
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              </>
            ) : (
              <>
                <Button
                  variant="default"
                  onClick={() => router.push('/register')}
                >
                  Sign Up
                </Button>
                <Button variant="outline" onClick={() => router.push('/login')}>
                  Sign In
                </Button>
              </>
            )}
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="outline" size="icon">
                  <Sun className="h-[1.2rem] w-[1.2rem] scale-100 rotate-0 transition-all dark:scale-0 dark:-rotate-90" />
                  <Moon className="absolute h-[1.2rem] w-[1.2rem] scale-0 rotate-90 transition-all dark:scale-100 dark:rotate-0" />
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
          </div>
        </div>
      </div>
    </header>
  )
}
