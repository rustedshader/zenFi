'use client'

import { useEffect, useState } from 'react'
import { RefreshCcw, AlertCircle, Clock, Globe, Search } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle
} from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger
} from '@/components/ui/accordion'
import { Alert, AlertDescription } from '@/components/ui/alert'

interface NewsItem {
  topic: string
  description: string
  content: string
  sources: string[]
  summary: string
  publishedAt: string
}

const cleanSource = (source: string): string => {
  return source.split('|').pop()?.trim() || source || 'Unknown source'
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

      const formattedNews: NewsItem[] = data.map((item: any) => ({
        topic: item.topic || 'Untitled News',
        description: item.description || 'No description available',
        content: item.content || 'No content available',
        sources:
          Array.isArray(item.sources) && item.sources.length > 0
            ? item.sources
            : ['Unknown source'],
        summary: item.summary || 'No summary available',
        publishedAt: new Date().toISOString().split('T')[0]
      }))

      setNews(formattedNews)
    } catch (error) {
      console.error('Error fetching news:', error)
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    fetchNews()
  }, [])

  const filteredNews = news.filter(
    item =>
      item.topic.toLowerCase().includes(filter.toLowerCase()) ||
      item.summary.toLowerCase().includes(filter.toLowerCase()) ||
      item.description.toLowerCase().includes(filter.toLowerCase()) ||
      item.sources.some(source =>
        source.toLowerCase().includes(filter.toLowerCase())
      )
  )

  return (
    <div className="max-w-4xl mx-auto p-6 space-y-6">
      <div className="space-y-4">
        <h1 className="text-3xl font-bold">News</h1>

        <Accordion type="single" collapsible className="w-full">
          <AccordionItem value="about-zenfi">
            <AccordionTrigger>About Zenfi News</AccordionTrigger>
            <AccordionContent>
              <div className="space-y-2 text-sm text-muted-foreground">
                <p>
                  Zenfi News provides real-time financial and market updates
                  powered by AI-driven analysis. Our platform aggregates news
                  from trusted sources to keep you informed about the latest
                  market movements, corporate developments, and economic trends.
                </p>
                <p>
                  Stay ahead of the market with curated news stories,
                  comprehensive summaries, and direct links to original sources
                  for deeper insights.
                </p>
              </div>
            </AccordionContent>
          </AccordionItem>
        </Accordion>
      </div>

      <div className="flex gap-4 items-center">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
          <Input
            type="text"
            placeholder="Filter news..."
            className="pl-10"
            value={filter}
            onChange={e => setFilter(e.target.value)}
          />
        </div>
        <Button onClick={fetchNews} disabled={isLoading} variant="outline">
          <RefreshCcw
            className={`h-4 w-4 mr-2 ${isLoading ? 'animate-spin' : ''}`}
          />
          Refresh
        </Button>
      </div>

      {isLoading && news.length === 0 && (
        <div className="flex justify-center items-center h-64">
          <div className="text-center space-y-2">
            <RefreshCcw className="h-8 w-8 animate-spin mx-auto text-muted-foreground" />
            <p className="text-muted-foreground">Loading the latest news...</p>
          </div>
        </div>
      )}

      {!isLoading && news.length === 0 && (
        <Alert>
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            No news available. Check your connection or try again later.
          </AlertDescription>
        </Alert>
      )}

      {filteredNews.length === 0 && filter && !isLoading && (
        <Alert>
          <AlertDescription>No results found for "{filter}"</AlertDescription>
        </Alert>
      )}

      <div className="space-y-4">
        {filteredNews.map((item, index) => (
          <Card key={index}>
            <CardHeader>
              <CardTitle className="text-lg">{item.topic}</CardTitle>
              <CardDescription>{item.description}</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <p className="text-sm">{item.summary}</p>

              <Accordion type="single" collapsible className="w-full">
                <AccordionItem value={`content-${index}`}>
                  <AccordionTrigger>Read Full News</AccordionTrigger>
                  <AccordionContent>
                    <p className="text-sm">{item.content}</p>
                  </AccordionContent>
                </AccordionItem>
              </Accordion>

              <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 text-xs text-muted-foreground">
                <div className="flex items-center gap-2 max-w-[70%] sm:max-w-[50%]">
                  <Globe className="h-3 w-3 flex-shrink-0" />
                  <span className="truncate">
                    {item.sources.length > 0
                      ? cleanSource(item.sources[0])
                      : 'Unknown source'}
                  </span>
                  {item.sources.length > 1 && (
                    <Badge
                      variant="secondary"
                      className="text-xs flex-shrink-0"
                    >
                      +{item.sources.length - 1} more
                    </Badge>
                  )}
                </div>
                <div className="flex items-center gap-2">
                  <Clock className="h-3 w-3" />
                  <span>{new Date(item.publishedAt).toLocaleDateString()}</span>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {news.length > 0 && (
        <div className="text-center text-sm text-muted-foreground">
          Showing {filteredNews.length} of {news.length} news items
        </div>
      )}
    </div>
  )
}
