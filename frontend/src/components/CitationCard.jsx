export default function CitationCard({ citation, index }) {
  const scorePercent = Math.round((citation.relevance_score ?? 0) * 100)

  const typeColors = {
    sop:              'bg-purple-100 text-purple-700',
    manual:           'bg-blue-100 text-blue-700',
    safety_guideline: 'bg-red-100 text-red-700',
    shipping_protocol:'bg-green-100 text-green-700',
  }
  const typeLabel = typeColors[citation.document_type] ?? 'bg-gray-100 text-gray-600'

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2 min-w-0">
          <span className="flex-shrink-0 flex items-center justify-center w-5 h-5 rounded-full bg-brand-100 text-brand-700 text-xs font-bold">
            {index}
          </span>
          <p className="text-sm font-semibold text-gray-800 truncate">
            {citation.document_name}
          </p>
        </div>
        <span className={`flex-shrink-0 text-xs font-medium px-2 py-0.5 rounded-full ${typeLabel}`}>
          {citation.document_type ?? 'manual'}
        </span>
      </div>

      <div className="mt-2 flex flex-wrap gap-3 text-xs text-gray-500">
        <span>Page {citation.page_number}</span>
        {citation.section_title && (
          <span className="truncate">§ {citation.section_title}</span>
        )}
        <span className="ml-auto font-medium text-brand-600">{scorePercent}% match</span>
      </div>

      {citation.excerpt && (
        <p className="mt-2 text-xs text-gray-600 leading-relaxed line-clamp-3">
          {citation.excerpt}
        </p>
      )}
    </div>
  )
}
