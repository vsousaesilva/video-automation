import ReactPlayer from 'react-player'

export default function DualVideoPreview({ verticalUrl, horizontalUrl }) {
  const hasVertical = !!verticalUrl
  const hasHorizontal = !!horizontalUrl

  if (!hasVertical && !hasHorizontal) {
    return (
      <div className="text-center py-8 text-gray-400 text-sm">
        Nenhum vídeo disponível para preview.
      </div>
    )
  }

  return (
    <div className="flex gap-4 flex-wrap">
      {/* Vertical 9:16 */}
      {hasVertical && (
        <div className="flex-shrink-0">
          <p className="text-xs font-medium text-gray-500 mb-2 text-center">Vertical (9:16)</p>
          <div className="w-[180px] h-[320px] bg-black rounded-lg overflow-hidden">
            <ReactPlayer
              url={verticalUrl}
              width="100%"
              height="100%"
              controls
              light
              pip
            />
          </div>
        </div>
      )}

      {/* Horizontal 16:9 */}
      {hasHorizontal && (
        <div className="flex-1 min-w-[280px]">
          <p className="text-xs font-medium text-gray-500 mb-2 text-center">Horizontal (16:9)</p>
          <div className="aspect-video bg-black rounded-lg overflow-hidden">
            <ReactPlayer
              url={horizontalUrl}
              width="100%"
              height="100%"
              controls
              light
              pip
            />
          </div>
        </div>
      )}
    </div>
  )
}
