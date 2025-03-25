import { cn } from '@/lib/utils'
import { ChevronDown, ChevronUp } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Button } from './ui/button'

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
  return (
    <div className="bg-muted/50 rounded-lg p-4">
      <div className={cn('prose max-w-full break-words', isOpen ? '' : '')}>
        <ReactMarkdown
          remarkPlugins={[remarkGfm]}
          components={{
            p: ({ children }) => <p className="mb-2">{children}</p>,
            ul: ({ children }) => (
              <ul className="list-disc pl-4 mb-2">{children}</ul>
            ),
            ol: ({ children }) => (
              <ol className="list-decimal pl-4 mb-2">{children}</ol>
            ),
            li: ({ children }) => <li className="mb-1">{children}</li>,
            h1: ({ children }) => (
              <h1 className="text-2xl font-bold mb-2">{children}</h1>
            ),
            h2: ({ children }) => (
              <h2 className="text-xl font-bold mb-2">{children}</h2>
            ),
            h3: ({ children }) => (
              <h3 className="text-lg font-bold mb-2">{children}</h3>
            ),
            code: ({ children }) => (
              <code className="bg-muted p-1 rounded">{children}</code>
            )
          }}
        >
          {content}
        </ReactMarkdown>
      </div>

      {/* Sources section */}
      {sources && sources.length > 0 && (
        <div className="mt-4 text-sm">
          <div className="flex items-center justify-between">
            <span>Sources</span>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => onOpenChange(!isOpen)}
              className="hover:bg-transparent"
            >
              {isOpen ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
            </Button>
          </div>
          {isOpen && (
            <ul className="mt-2 space-y-2 text-xs">
              {sources.map((source, index) => (
                <li key={index} className="bg-background p-2 rounded">
                  {JSON.stringify(source)}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  )
}
