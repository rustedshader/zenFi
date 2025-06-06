import { cn } from '@/lib/utils'
import { ChevronDown, ChevronUp, Copy } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Button } from './ui/button'
import { SearchResults } from './search-results'
import { motion, AnimatePresence } from 'framer-motion'
import { toast } from 'sonner'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism'

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
      // The 'prose' class provides typographic defaults.
      // 'max-w-none' here means this component will try to fill its parent's width.
      // If AnswerSection itself should have a max-width, apply it here.
      // Otherwise, width control is deferred to the parent or the inner content div.
      className="prose dark:prose-invert max-w-none"
    >
      <div className="flex items-start gap-3 p-4">
        <div className="flex-1 space-y-3">
          {/* This container has overflow-hidden, which will clip content if it somehow still overflows its bounds. */}
          <div className="space-y-4 overflow-hidden">
            {/*
              This div applies prose styling to the Markdown content.
              To achieve a "fixed horizontal length" for the text:
              1. Remove 'max-w-none' (if present) to use the default 'prose' max-width (good for readability).
              2. Or, set a specific Tailwind max-width class e.g., 'max-w-2xl', 'max-w-3xl'.
              Here, we remove 'max-w-none' to rely on the 'prose-sm' default max-width.
            */}
            <div className="prose prose-sm dark:prose-invert max-w-4xl">
              {' '}
              {/* MODIFICATION: Removed max-w-none */}
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                components={{
                  p: ({ children }) => (
                    <p className="text-base leading-relaxed whitespace-pre-wrap break-words">
                      {/*
                        'whitespace-pre-wrap' ensures text wraps and newlines (if any) are respected.
                        'break-words' (CSS overflow-wrap: break-word) is added as a safeguard
                        to break very long unbreakable strings (e.g., a long token without spaces)
                        to prevent overflow. Tailwind's 'prose' often includes this, but being explicit helps.
                      */}
                      {children}
                    </p>
                  ),
                  a: ({ href, children }) => {
                    // ... (your existing link styling is fine)
                    if (
                      href?.includes('youtube.com') ||
                      href?.includes('youtu.be')
                    ) {
                      return (
                        <a
                          href={href}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-blue-500 break-all" // Added break-all for very long URLs
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
                        className="text-blue-500 break-all" // Added break-all for very long URLs
                      >
                        {children}
                      </a>
                    )
                  },
                  code({ node, inline, className, children, ...props }) {
                    const match = /language-(\w+)/.exec(className || '')
                    return !inline && match ? (
                      <SyntaxHighlighter
                        style={vscDarkPlus as any}
                        language={match[1]}
                        PreTag="div"
                        // 'overflow-x-auto' makes code blocks scrollable horizontally for long lines.
                        // Duplicate 'rounded-md' removed.
                        className="rounded-md overflow-x-auto" // MODIFICATION: Corrected duplicate class
                        {...props}
                      >
                        {String(children).replace(/\n$/, '')}
                      </SyntaxHighlighter>
                    ) : (
                      <code
                        className={cn(
                          'rounded bg-muted px-1 py-0.5 font-mono text-sm break-words', // Added break-words for inline code
                          className
                        )}
                        {...props}
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
