import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Card, CardHeader, CardTitle, CardContent } from '../ui/card'

export default function AiPorfolioInsights() {
  return (
    <>
      <Card className="mb-8">
        <CardHeader>
          <CardTitle className="flex items-center">
            <span className="bg-gradient-to-r from-purple-600 to-blue-600 bg-clip-text text-transparent">
              AI Portfolio Insights
            </span>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="prose prose-sm max-w-none dark:prose-invert min-h-[100px]">
            {portfolio.ai_summary ? (
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {portfolio.ai_summary}
              </ReactMarkdown>
            ) : (
              <p className="text-muted-foreground">No AI insights available.</p>
            )}
          </div>
        </CardContent>
      </Card>
    </>
  )
}
