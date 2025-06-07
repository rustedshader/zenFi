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

// Function to remove markdown code block wrappers
const cleanMarkdownContent = (content: string): string => {
  // Remove ```markdown ... ``` blocks and similar patterns
  const markdownBlockRegex = /^```(?:markdown|md)?\s*\n?([\s\S]*?)\n?```$/gm

  // First, try to match and extract content from markdown blocks
  const matches = content.match(markdownBlockRegex)
  if (matches) {
    // Replace each markdown block with just its inner content
    let cleaned = content
    matches.forEach(match => {
      const innerContent = match
        .replace(/^```(?:markdown|md)?\s*\n?/, '')
        .replace(/\n?```$/, '')
      cleaned = cleaned.replace(match, innerContent.trim())
    })
    return cleaned
  }

  // If no markdown blocks found, return original content
  return content
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

  // Clean the content before passing to ReactMarkdown
  const cleanedContent = cleanMarkdownContent(content)

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
            <div className="prose prose-sm dark:prose-invert max-w-4xl">
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                components={{
                  p: ({ children }) => (
                    <p className="text-base leading-relaxed whitespace-pre-wrap break-words">
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
                          className="text-blue-500 break-all"
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
                        className="text-blue-500 break-all"
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
                        className="rounded-md overflow-x-auto"
                        {...props}
                      >
                        {String(children).replace(/\n$/, '')}
                      </SyntaxHighlighter>
                    ) : (
                      <code
                        className={cn(
                          'rounded bg-muted px-1 py-0.5 font-mono text-sm break-words',

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
                {cleanedContent}
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
