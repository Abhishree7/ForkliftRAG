import CitationCard from './CitationCard'

export default function MessageBubble({ message }) {
  const isUser = message.role === 'user'

  return (
    <div className={`flex flex-col gap-1 ${isUser ? 'items-end' : 'items-start'}`}>
      <span className="text-xs text-gray-400 px-1">
        {isUser ? 'You' : 'Unisco Assistant'}
      </span>

      {/* Bubble */}
      <div
        className={`max-w-2xl rounded-2xl px-4 py-3 text-sm leading-relaxed shadow-sm ${
          isUser
            ? 'bg-brand-600 text-white rounded-br-sm'
            : 'bg-white border border-gray-200 text-gray-800 rounded-bl-sm'
        }`}
      >
        {message.content}
      </div>

      {/* Metadata row (assistant only) */}
      {!isUser && message.metadata && (
        <div className="flex flex-wrap items-center gap-3 px-1 text-xs text-gray-400">
          {message.metadata.cache_hit && (
            <span className="flex items-center gap-1 text-amber-500 font-medium">
              <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                <path d="M10 2a8 8 0 100 16A8 8 0 0010 2zm1 11H9V9h2v4zm0-6H9V5h2v2z"/>
              </svg>
              Cached
            </span>
          )}
          <span>{message.metadata.search_time_ms?.toFixed(0)} ms</span>
          <span>{message.metadata.query_type_used}</span>
          <span>{message.metadata.total_documents_searched} chunks searched</span>
        </div>
      )}

      {/* Citations (assistant only) */}
      {!isUser && message.citations?.length > 0 && (
        <div className="w-full max-w-2xl mt-1 space-y-2">
          <p className="text-xs font-semibold text-gray-500 px-1">
            Sources ({message.citations.length})
          </p>
          {message.citations.map((c, i) => (
            <CitationCard key={`${c.document_id}-${c.page_number}-${i}`} citation={c} index={i + 1} />
          ))}
        </div>
      )}

      {/* Error state */}
      {!isUser && message.error && (
        <div className="max-w-2xl rounded-xl bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700">
          {message.content}
        </div>
      )}
    </div>
  )
}
