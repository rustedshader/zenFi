import 'katex/dist/katex.min.css'
import rehypeExternalLinks from 'rehype-external-links'
import rehypeKatex from 'rehype-katex'
import remarkGfm from 'remark-gfm'
import remarkMath from 'remark-math'
import { Citing } from './custom-link'
import { CodeBlock } from './ui/codeblock'
import { MemoizedReactMarkdown } from './ui/markdown'

export function BotMessage({
  message,
  className
}: {
  message: string
  className?: string
}) {
  // Check if the content contains LaTeX patterns
  const containsLaTeX = /\\\[([\s\S]*?)\\\]|\\\(([\s\S]*?)\\\)/.test(
    message || ''
  )
  // Preprocess LaTeX equations
  const processedData = preprocessLaTeX(message || '')
  // Base container classes for the assistant message bubble

  if (containsLaTeX) {
    return (
      <div>
        <MemoizedReactMarkdown
          rehypePlugins={[
            [rehypeExternalLinks, { target: '_blank' }],
            [rehypeKatex]
          ]}
          remarkPlugins={[remarkGfm, remarkMath]}
          className="prose-sm prose-neutral prose-a:text-accent-foreground/50"
        >
          {processedData}
        </MemoizedReactMarkdown>
      </div>
    )
  }

  return (
    <div>
      <MemoizedReactMarkdown
        rehypePlugins={[[rehypeExternalLinks, { target: '_blank' }]]}
        remarkPlugins={[remarkGfm]}
        className="prose-sm prose-neutral prose-a:text-accent-foreground/50"
        components={{
          code({ node, inline, className, children, ...props }) {
            if (children.length) {
              if (children[0] == '▍') {
                return (
                  <span className="mt-1 cursor-default animate-pulse">▍</span>
                )
              }
              children[0] = (children[0] as string).replace('`▍`', '▍')
            }
            const match = /language-(\w+)/.exec(className || '')
            if (inline) {
              return (
                <code className={className} {...props}>
                  {children}
                </code>
              )
            }
            return (
              <CodeBlock
                key={Math.random()}
                language={(match && match[1]) || ''}
                value={String(children).replace(/\n$/, '')}
                {...props}
              />
            )
          },
          a: Citing
        }}
      >
        {message}
      </MemoizedReactMarkdown>
    </div>
  )
}

const preprocessLaTeX = (content: string) => {
  const blockProcessedContent = content.replace(
    /\\\[([\s\S]*?)\\\]/g,
    (_, equation) => `$$${equation}$$`
  )
  const inlineProcessedContent = blockProcessedContent.replace(
    /\\\(([\s\S]*?)\\\)/g,
    (_, equation) => `$${equation}$`
  )
  return inlineProcessedContent
}
