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
import Image from 'next/image'

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
      color: isLive ? 'text-green-600 border' : 'text-red-600 border',
      icon: isLive ? Activity : Clock
    }
  }

  // const fetchMarketStatus = async () => {
  //   if (!isLoggedIn) {
  //     setMarketStatus('') // Clear market status if not logged in
  //     return
  //   }

  //   try {
  //     const response = await fetch('/api/dashboard/market_status', {
  //       credentials: 'include' // Include cookies
  //     })
  //     if (!response.ok) throw new Error('Failed to fetch market info')
  //     const data: DashboardInfo = await response.json()
  //     setMarketStatus(data.market_status)
  //   } catch (error) {
  //     console.error('Error fetching market status:', error)
  //     setMarketStatus('')
  //   }
  // }

  // const interval = setInterval(fetchMarketStatus, 300000)

  const handleLogout = () => {
    router.push(`/login`)
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
        credentials: 'include' // Include cookies
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
    // fetchMarketStatus()
    // return () => clearInterval(interval)
  }, [isLoggedIn])

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
    <header className="border-b shadow-sm">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          <div className="flex items-center gap-6">
            <span className="relative h-10 w-10">
              <Image
                src="/zenfi_logo.png"
                alt="zenfi_logo"
                height={40}
                width={40}
                priority
                className="block"
              />
            </span>
            <Link href="/" className="flex items-center gap-2">
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
                  className="pl-10 pr-4 border focus:border-transparent"
                />
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              </form>

              {isDropdownOpen && searchResults.length > 0 && (
                <div className="absolute z-50 w-full mt-1 bg-background border rounded-lg shadow-lg max-h-96 overflow-y-auto">
                  {isLoading ? (
                    <div className="p-4 text-center text-muted-foreground">
                      <div className="animate-spin rounded-full h-4 w-4 border-2 mx-auto"></div>
                    </div>
                  ) : (
                    searchResults.map(stock => (
                      <div
                        key={stock.symbol}
                        className="p-3 cursor-pointer hover:bg-muted border-b last:border-b-0"
                        onClick={() => handleResultClick(stock.symbol)}
                      >
                        <div className="flex justify-between items-start">
                          <span className="font-semibold">{stock.symbol}</span>
                          <span className="text-sm px-2 py-0.5 rounded">
                            {stock.exchDisp}
                          </span>
                        </div>
                        <div className="text-sm mt-1">{stock.longname}</div>
                        {stock.sector && stock.industry && (
                          <div className="text-xs mt-1">
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

          <div className="flex items-center gap-2">
            {isLoggedIn ? (
              <>
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
                  variant="default"
                  onClick={() => router.push('/register')}
                  className="border rounded-full"
                >
                  Sign Up
                </Button>
                <Button
                  variant="ghost"
                  onClick={() => router.push('/login')}
                  className="border rounded-full"
                >
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
