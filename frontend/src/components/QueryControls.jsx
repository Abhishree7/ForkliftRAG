const QUERY_TYPES = [
  { value: 'hybrid',   label: 'Hybrid',   description: 'Semantic + keyword (recommended)' },
  { value: 'semantic', label: 'Semantic',  description: 'Meaning-based search' },
  { value: 'keyword',  label: 'Keyword',   description: 'Exact term matching' },
]

export default function QueryControls({ queryType, maxResults, onChange }) {
  return (
    <div className="flex flex-wrap items-center gap-4">
      {/* Query type toggle */}
      <div className="flex items-center gap-1 rounded-lg bg-gray-100 p-1">
        {QUERY_TYPES.map(({ value, label }) => (
          <button
            key={value}
            onClick={() => onChange({ queryType: value })}
            title={QUERY_TYPES.find(q => q.value === value)?.description}
            className={`px-3 py-1 rounded-md text-xs font-medium transition-colors ${
              queryType === value
                ? 'bg-white text-brand-600 shadow-sm'
                : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {/* Max results */}
      <div className="flex items-center gap-2">
        <label className="text-xs text-gray-500 whitespace-nowrap">Max results</label>
        <select
          value={maxResults}
          onChange={e => onChange({ maxResults: Number(e.target.value) })}
          className="text-xs rounded-md border border-gray-200 bg-white py-1 pl-2 pr-6 text-gray-700 focus:outline-none focus:ring-1 focus:ring-brand-500"
        >
          {[3, 5, 8, 10].map(n => (
            <option key={n} value={n}>{n}</option>
          ))}
        </select>
      </div>
    </div>
  )
}
