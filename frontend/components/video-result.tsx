import Image from 'next/image'

interface VideoResultProps {
  title: string
  url: string
  thumbnail?: string
  description?: string
}

export function VideoResult({
  title,
  url,
  thumbnail,
  description
}: VideoResultProps) {
  // Extract video ID from YouTube URL
  const getVideoId = (url: string) => {
    const regExp =
      /^.*(youtu.be\/|v\/|u\/\w\/|embed\/|watch\?v=|&v=)([^#&?]*).*/
    const match = url.match(regExp)
    return match && match[2].length === 11 ? match[2] : null
  }

  const videoId = getVideoId(url)
  const thumbnailUrl =
    thumbnail ||
    (videoId ? `https://img.youtube.com/vi/${videoId}/maxresdefault.jpg` : null)

  return (
    <div className="flex flex-col gap-2 p-3 sm:p-4 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
      <div className="flex flex-col sm:flex-row gap-3 sm:gap-4">
        {thumbnailUrl && (
          <div className="flex-shrink-0 w-full sm:w-48">
            <Image
              src={thumbnailUrl}
              alt={title}
              width={192}
              height={108}
              className="w-full h-48 sm:h-28 rounded-lg object-cover"
              onError={e => {
                const target = e.target as HTMLImageElement
                target.src = `https://img.youtube.com/vi/${videoId}/hqdefault.jpg`
              }}
            />
          </div>
        )}
        <div className="flex-1 min-w-0">
          <a
            href={url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-blue-600 dark:text-blue-400 hover:underline font-medium text-sm sm:text-base"
          >
            {title}
          </a>
          {description && (
            <p className="mt-1 text-xs sm:text-sm text-gray-600 dark:text-gray-300 line-clamp-2">
              {description}
            </p>
          )}
        </div>
      </div>
    </div>
  )
}
