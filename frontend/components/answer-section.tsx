import { cn } from '@/lib/utils'
import { ChevronDown, ChevronUp, Copy } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Button } from './ui/button'
import { SearchResults } from './search-results'
import { motion, AnimatePresence } from 'framer-motion'
import { toast } from 'sonner'

interface AnswerSectionProps {
  content: string
  isOpen: boolean
  onOpenChange: (open: boolean) => void
  chatId?: string
  sources?: any[]
  timestamp?: number
  isLoading?: boolean
}

export function AnswerSection({
  content,
  isOpen,
  onOpenChange,
  chatId,
  sources,
  timestamp,
  isLoading = false
}: AnswerSectionProps) {
  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(content)
      toast.success('Copied to clipboard')
    } catch (err) {
      toast.error('Failed to copy')
    }
  }

  // Process sources to identify videos and web results
  const processedSources =
    sources?.map(source => {
      if (
        typeof source === 'string' &&
        (source.includes('youtube.com') || source.includes('youtu.be'))
      ) {
        return {
          type: 'video' as const,
          url: source,
          title: 'YouTube Video',
          description: 'Click to watch the video'
        }
      }
      return {
        type: 'web' as const,
        url: source,
        title: source,
        description: ''
      }
    }) || []

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="prose dark:prose-invert max-w-none"
    >
      <div className="flex items-start gap-3 p-4">
        <div className="flex-1 space-y-3">
          <div className="space-y-4 overflow-hidden">
            <div className="prose prose-sm dark:prose-invert max-w-none">
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                components={{
                  p: ({ children }) => (
                    <p className="text-base leading-relaxed whitespace-pre-wrap text-gray-700 dark:text-gray-200">
                      {children}
                    </p>
                  ),
                  a: ({ href, children }) => {
                    if (
                      href?.includes('youtube.com') ||
                      href?.includes('youtu.be')
                    ) {
                      return (
                        <a
                          href={href}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-blue-500 hover:text-blue-600 dark:text-blue-400 dark:hover:text-blue-300"
                        >
                          {children}
                        </a>
                      )
                    }
                    return (
                      <a
                        href={href}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-blue-500 hover:text-blue-600 dark:text-blue-400 dark:hover:text-blue-300"
                      >
                        {children}
                      </a>
                    )
                  },
                  code: ({ inline, className, children, ...props }) => {
                    const match = /language-(\w+)/.exec(className || '')
                    return !inline && match ? (
                      <code
                        className={className}
                        {...props}
                        style={{
                          backgroundColor: 'transparent',
                          padding: '0.5rem',
                          borderRadius: '0.375rem',
                          fontSize: '0.875rem',
                          lineHeight: '1.5',
                          display: 'block',
                          overflowX: 'auto'
                        }}
                      >
                        {children}
                      </code>
                    ) : (
                      <code
                        className={className}
                        {...props}
                        style={{
                          backgroundColor: 'rgba(0, 0, 0, 0.05)',
                          padding: '0.2em 0.4em',
                          borderRadius: '0.25rem',
                          fontSize: '0.875em',
                          lineHeight: '1.5'
                        }}
                      >
                        {children}
                      </code>
                    )
                  }
                }}
              >
                {content}
              </ReactMarkdown>
            </div>
            {!isLoading && (
              <div className="flex justify-end items-center gap-2 pt-2 border-t border-gray-100 dark:border-gray-800">
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={handleCopy}
                  className="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
                >
                  <Copy className="size-4" />
                </Button>
              </div>
            )}
          </div>
        </div>
      </div>
      {processedSources.length > 0 && (
        <div className="mt-4">
          <SearchResults results={processedSources} />
        </div>
      )}
    </motion.div>
  )
}
