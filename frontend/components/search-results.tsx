import { VideoResult } from './video-result'

interface SearchResult {
  title: string
  url: string
  description?: string
  thumbnail?: string
  type?: 'video' | 'web'
}

interface SearchResultsProps {
  results: SearchResult[]
}

export function SearchResults({ results }: SearchResultsProps) {
  const videos = results.filter(result => result.type === 'video')
  const webResults = results.filter(result => result.type !== 'video')

  return (
    <div className="space-y-4 sm:space-y-6">
      {videos.length > 0 && (
        <div className="space-y-3 sm:space-y-4">
          <h3 className="text-base sm:text-lg font-semibold text-gray-900 dark:text-gray-100">
            Videos
          </h3>
          <div className="grid gap-3 sm:gap-4 grid-cols-1 sm:grid-cols-2">
            {videos.map((video, index) => (
              <VideoResult
                key={index}
                title={video.title}
                url={video.url}
                thumbnail={video.thumbnail}
                description={video.description}
              />
            ))}
          </div>
        </div>
      )}

      {webResults.length > 0 && (
        <div className="space-y-3 sm:space-y-4">
          <h3 className="text-base sm:text-lg font-semibold text-gray-900 dark:text-gray-100">
            Web Results
          </h3>
          <div className="space-y-3 sm:space-y-4">
            {webResults.map((result, index) => (
              <div
                key={index}
                className="p-3 sm:p-4 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700"
              >
                <a
                  href={result.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-blue-600 dark:text-blue-400 hover:underline font-medium text-sm sm:text-base"
                >
                  {result.title}
                </a>
                {result.description && (
                  <p className="mt-1 text-xs sm:text-sm text-gray-600 dark:text-gray-300">
                    {result.description}
                  </p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
