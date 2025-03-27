import { cn } from '@/lib/utils'
import { ChevronDown, ChevronUp } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Button } from './ui/button'
import { SearchResults } from './search-results'

interface AnswerSectionProps {
  content: string
  isOpen: boolean
  onOpenChange: (open: boolean) => void
  chatId?: string
  sources?: any[]
}

export function AnswerSection({
  content,
  isOpen,
  onOpenChange,
  chatId,
  sources
}: AnswerSectionProps) {
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
    <div className="prose dark:prose-invert max-w-none">
      <div className="flex items-start gap-2">
        <div className="flex-shrink-0 mt-1">
          <div className="size-6 rounded-full bg-gray-100 dark:bg-gray-700 flex items-center justify-center">
            <svg
              className="size-4 text-gray-600 dark:text-gray-300"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
              xmlns="http://www.w3.org/2000/svg"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"
              />
            </svg>
          </div>
        </div>
        <div className="flex-1">
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            components={{
              p: ({ children }) => (
                <p className="text-base leading-relaxed whitespace-pre-wrap">
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
                      className="inline-flex items-center gap-1 text-blue-600 dark:text-blue-400 hover:underline"
                    >
                      <svg
                        className="size-4"
                        viewBox="0 0 24 24"
                        fill="currentColor"
                      >
                        <path d="M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z" />
                      </svg>
                      {children}
                    </a>
                  )
                }
                return (
                  <a
                    href={href}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-blue-600 dark:text-blue-400 hover:underline"
                  >
                    {children}
                  </a>
                )
              }
            }}
          >
            {content}
          </ReactMarkdown>
        </div>
      </div>

      {/* Sources section */}
      {processedSources.length > 0 && (
        <div className="mt-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
              Sources & References
            </h3>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => onOpenChange(!isOpen)}
              className="hover:bg-transparent"
            >
              {isOpen ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
            </Button>
          </div>
          {isOpen && <SearchResults results={processedSources} />}
        </div>
      )}
    </div>
  )
}
