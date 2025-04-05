'use client'

import { useEffect, useState } from 'react'
import { toast } from 'sonner'
import {
  RefreshCcw,
  AlertCircle,
  ChevronRight,
  Clock,
  Globe
} from 'lucide-react'

interface NewsItem {
  headline: string
  summary: string
  source: string
  publishedAt: string
}

interface NewsResponse {
  news: NewsItem[]
}

export default function NewsFeed() {
  const [news, setNews] = useState<NewsItem[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [filter, setFilter] = useState('')

  const fetchNews = async () => {
    setIsLoading(true)
    try {
      const response = await fetch('/api/news')
      if (!response.ok) {
        throw new Error('Failed to fetch news')
      }
      const data = await response.json()
      // If data.news exists, use it; otherwise, assume data is the news array
      setNews(data.news || data)
      toast.success('News updated successfully')
    } catch (error) {
      console.error('Error fetching news:', error)
      toast.error('Failed to update news')
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    fetchNews()
  }, [])

  const filteredNews = news.filter(
    item =>
      item.headline.toLowerCase().includes(filter.toLowerCase()) ||
      item.summary.toLowerCase().includes(filter.toLowerCase()) ||
      item.source.toLowerCase().includes(filter.toLowerCase())
  )

  return (
    <div className="max-w-4xl mx-auto p-6">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-3xl font-bold text-slate-800">
          <span className="text-blue-600">Zenfi AI</span> News
        </h1>
        <div className="flex items-center gap-4">
          <div className="relative">
            <input
              type="text"
              placeholder="Filter news..."
              className="px-4 py-2 pr-8 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              value={filter}
              onChange={e => setFilter(e.target.value)}
            />
            {filter && (
              <button
                className="absolute right-2 top-2.5 text-gray-400 hover:text-gray-600"
                onClick={() => setFilter('')}
              >
                ×
              </button>
            )}
          </div>
          <button
            onClick={fetchNews}
            disabled={isLoading}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50"
          >
            <RefreshCcw size={16} className={isLoading ? 'animate-spin' : ''} />
            Refresh
          </button>
        </div>
      </div>

      {isLoading && news.length === 0 && (
        <div className="flex justify-center items-center h-64">
          <div className="text-center">
            <RefreshCcw
              size={32}
              className="animate-spin mx-auto mb-4 text-blue-600"
            />
            <p className="text-gray-600">Loading the latest news...</p>
          </div>
        </div>
      )}

      {!isLoading && news.length === 0 && (
        <div className="flex justify-center items-center h-64 border-2 border-dashed rounded-lg bg-gray-50">
          <div className="text-center p-6">
            <AlertCircle size={32} className="mx-auto mb-4 text-amber-500" />
            <h3 className="text-lg font-medium text-gray-900">
              No news available
            </h3>
            <p className="mt-1 text-gray-600">
              Check your connection or try again later.
            </p>
          </div>
        </div>
      )}

      {filteredNews.length === 0 && filter && !isLoading && (
        <div className="text-center p-8 bg-gray-50 rounded-lg">
          <p className="text-gray-600">
            No results found for &quot;{filter}&quot;
          </p>
        </div>
      )}

      <div className="grid gap-6">
        {filteredNews.map((item, index) => (
          <div
            key={index}
            className="bg-white border border-gray-200 rounded-xl overflow-hidden shadow-sm hover:shadow-md transition-shadow"
          >
            <div className="p-6">
              <h2 className="text-xl font-semibold text-gray-900 mb-2 line-clamp-2">
                {item.headline}
              </h2>
              <p className="text-gray-700 mb-4 line-clamp-3">{item.summary}</p>
              <div className="flex justify-between items-center text-sm">
                <div className="flex items-center gap-2 text-gray-500">
                  <Globe size={14} className="text-blue-500" />
                  <span>{item.source}</span>
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>

      {news.length > 0 && (
        <div className="mt-6 text-center text-gray-500 text-sm">
          Showing {filteredNews.length} of {news.length} news items
        </div>
      )}
    </div>
  )
}
