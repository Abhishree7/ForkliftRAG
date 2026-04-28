export default function Sidebar({ companyId, onCompanyIdChange, isConnected }) {
  return (
    <aside className="flex flex-col w-72 bg-white border-r border-gray-200 p-5 gap-6">
      {/* Logo / Brand */}
      <div className="flex items-center gap-2">
        <div className="w-8 h-8 rounded-lg bg-brand-600 flex items-center justify-center">
          <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
              d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
        </div>
        <span className="font-bold text-gray-900 text-lg">Unisco RAG</span>
      </div>

      {/* Connection status */}
      <div className="flex items-center gap-2 text-xs">
        <span className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-400' : 'bg-red-400'}`} />
        <span className="text-gray-500">
          {isConnected ? 'API connected' : 'API unreachable'}
        </span>
      </div>

      {/* Company ID */}
      <div className="flex flex-col gap-1.5">
        <label className="text-xs font-semibold text-gray-600 uppercase tracking-wide">
          Company ID
        </label>
        <input
          type="text"
          value={companyId}
          onChange={e => onCompanyIdChange(e.target.value)}
          placeholder="Paste your UUID here"
          className="w-full rounded-lg border border-gray-200 px-3 py-2 text-xs text-gray-800 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-brand-500 font-mono"
        />
        <p className="text-xs text-gray-400 leading-snug">
          Must match the ID used when ingesting documents.
        </p>
      </div>

      {/* How it works */}
      <div className="flex flex-col gap-3 mt-auto">
        <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">How it works</p>
        {[
          { step: '1', label: 'Ingest documents', desc: 'Run ingest_document.py with your PDF/DOCX' },
          { step: '2', label: 'Set Company ID', desc: 'Use the UUID from your ingest run' },
          { step: '3', label: 'Ask questions', desc: 'Claude answers from your documents only' },
        ].map(({ step, label, desc }) => (
          <div key={step} className="flex gap-3">
            <span className="flex-shrink-0 w-5 h-5 rounded-full bg-brand-100 text-brand-700 text-xs font-bold flex items-center justify-center">
              {step}
            </span>
            <div>
              <p className="text-xs font-medium text-gray-700">{label}</p>
              <p className="text-xs text-gray-400">{desc}</p>
            </div>
          </div>
        ))}
      </div>
    </aside>
  )
}
