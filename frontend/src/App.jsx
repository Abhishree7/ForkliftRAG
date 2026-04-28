import { useState, useEffect, useRef, useCallback } from 'react'
import Sidebar from './components/Sidebar'
import MessageBubble from './components/MessageBubble'
import QueryControls from './components/QueryControls'

const API_BASE = 'http://localhost:8000'

function useApiHealth() {
  const [isConnected, setIsConnected] = useState(false)

  useEffect(() => {
    const check = async () => {
      try {
        const res = await fetch(`${API_BASE}/health`, { signal: AbortSignal.timeout(3000) })
        setIsConnected(res.ok)
      } catch {
        setIsConnected(false)
      }
    }
    check()
    const id = setInterval(check, 10000)
    return () => clearInterval(id)
  }, [])

  return isConnected
}

const LS_MESSAGES   = 'unisco_rag_messages'
const LS_COMPANY_ID = 'unisco_rag_company_id'

function loadFromStorage(key, fallback) {
  try {
    const raw = localStorage.getItem(key)
    return raw !== null ? JSON.parse(raw) : fallback
  } catch {
    return fallback
  }
}

export default function App() {
  const [messages,   setMessages]   = useState(() => loadFromStorage(LS_MESSAGES, []))
  const [input,      setInput]      = useState('')
  const [companyId,  setCompanyId]  = useState(() => loadFromStorage(LS_COMPANY_ID, ''))
  const [queryType,  setQueryType]  = useState('hybrid')
  const [maxResults, setMaxResults] = useState(5)
  const [loading,    setLoading]    = useState(false)
  const bottomRef = useRef(null)
  const inputRef  = useRef(null)
  const isConnected = useApiHealth()

  // Persist messages to localStorage whenever they change
  useEffect(() => {
    localStorage.setItem(LS_MESSAGES, JSON.stringify(messages))
  }, [messages])

  // Persist companyId to localStorage whenever it changes
  useEffect(() => {
    localStorage.setItem(LS_COMPANY_ID, JSON.stringify(companyId))
  }, [companyId])

  // Scroll to bottom on new message
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  const handleControlChange = useCallback((changes) => {
    if ('queryType' in changes) setQueryType(changes.queryType)
    if ('maxResults' in changes) setMaxResults(changes.maxResults)
  }, [])

  const sendMessage = async () => {
    const query = input.trim()
    if (!query || loading) return

    if (!companyId.trim()) {
      setMessages(prev => [...prev, {
        id: Date.now(),
        role: 'assistant',
        content: 'Please enter a Company ID in the sidebar before searching.',
        error: true,
      }])
      return
    }

    // Add user message
    setMessages(prev => [...prev, { id: Date.now(), role: 'user', content: query }])
    setInput('')
    setLoading(true)

    try {
      const res = await fetch(`${API_BASE}/api/v1/search`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query,
          company_id: companyId.trim(),
          query_type: queryType,
          max_results: maxResults,
        }),
      })

      const data = await res.json()

      if (!res.ok) {
        throw new Error(data?.detail?.error ?? data?.detail ?? 'Something went wrong.')
      }

      setMessages(prev => [...prev, {
        id: Date.now() + 1,
        role: 'assistant',
        content: data.response,
        citations: data.citations ?? [],
        metadata: data.metadata ?? {},
      }])
    } catch (err) {
      setMessages(prev => [...prev, {
        id: Date.now() + 1,
        role: 'assistant',
        content: err.message ?? 'Failed to reach the API. Make sure the backend is running.',
        error: true,
      }])
    } finally {
      setLoading(false)
      inputRef.current?.focus()
    }
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  const clearChat = () => {
    setMessages([])
    localStorage.removeItem(LS_MESSAGES)
  }

  return (
    <div className="flex h-full">
      <Sidebar
        companyId={companyId}
        onCompanyIdChange={setCompanyId}
        isConnected={isConnected}
      />

      {/* Main chat area */}
      <div className="flex flex-col flex-1 min-w-0">

        {/* Header */}
        <header className="flex items-center justify-between px-6 py-4 border-b border-gray-200 bg-white">
          <div>
            <h1 className="font-semibold text-gray-900">Logistics Document Assistant</h1>
            <p className="text-xs text-gray-400 mt-0.5">Ask anything about your manuals, SOPs, and guidelines</p>
          </div>
          {messages.length > 0 && (
            <button
              onClick={clearChat}
              className="text-xs text-gray-400 hover:text-red-500 transition-colors"
            >
              Clear chat
            </button>
          )}
        </header>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-6 py-6 space-y-6">
          {messages.length === 0 ? (
            <EmptyState />
          ) : (
            messages.map(msg => <MessageBubble key={msg.id} message={msg} />)
          )}

          {/* Loading indicator */}
          {loading && (
            <div className="flex items-start gap-2">
              <div className="bg-white border border-gray-200 rounded-2xl rounded-bl-sm px-4 py-3 shadow-sm">
                <div className="flex gap-1.5 items-center">
                  {[0, 150, 300].map(delay => (
                    <span
                      key={delay}
                      className="w-2 h-2 rounded-full bg-brand-400 animate-bounce"
                      style={{ animationDelay: `${delay}ms` }}
                    />
                  ))}
                </div>
              </div>
            </div>
          )}

          <div ref={bottomRef} />
        </div>

        {/* Input area */}
        <div className="border-t border-gray-200 bg-white px-6 py-4">
          <QueryControls
            queryType={queryType}
            maxResults={maxResults}
            onChange={handleControlChange}
          />

          <div className="flex items-end gap-3 mt-3">
            <textarea
              ref={inputRef}
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask about your logistics documents…"
              rows={1}
              className="flex-1 resize-none rounded-xl border border-gray-200 px-4 py-3 text-sm text-gray-800 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-brand-500 leading-relaxed"
              style={{ maxHeight: '8rem', overflowY: 'auto' }}
              onInput={e => {
                e.target.style.height = 'auto'
                e.target.style.height = `${Math.min(e.target.scrollHeight, 128)}px`
              }}
            />
            <button
              onClick={sendMessage}
              disabled={loading || !input.trim()}
              className="flex-shrink-0 flex items-center justify-center w-11 h-11 rounded-xl bg-brand-600 text-white hover:bg-brand-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
              aria-label="Send"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                  d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
              </svg>
            </button>
          </div>
          <p className="mt-2 text-xs text-gray-400">
            Press <kbd className="px-1 py-0.5 bg-gray-100 rounded text-gray-500 font-mono">Enter</kbd> to send,{' '}
            <kbd className="px-1 py-0.5 bg-gray-100 rounded text-gray-500 font-mono">Shift+Enter</kbd> for newline
          </p>
        </div>
      </div>
    </div>
  )
}

function EmptyState() {
  const examples = [
    'What are the pre-shift inspection steps for a forklift?',
    'What is the AMR minimum clearance distance?',
    'What safety gear is required in the warehouse?',
  ]

  return (
    <div className="flex flex-col items-center justify-center h-full text-center gap-6 py-16">
      <div className="w-14 h-14 rounded-2xl bg-brand-100 flex items-center justify-center">
        <svg className="w-8 h-8 text-brand-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
            d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
        </svg>
      </div>
      <div>
        <h2 className="font-semibold text-gray-800 text-lg">Ask your logistics documents</h2>
        <p className="text-sm text-gray-500 mt-1 max-w-sm">
          Answers are grounded in your uploaded manuals, SOPs, and guidelines — with citations.
        </p>
      </div>
      <div className="flex flex-col gap-2 w-full max-w-md">
        <p className="text-xs font-medium text-gray-400 uppercase tracking-wide">Try asking</p>
        {examples.map(ex => (
          <div key={ex} className="rounded-xl border border-gray-200 bg-white px-4 py-3 text-sm text-gray-600 text-left shadow-sm">
            {ex}
          </div>
        ))}
      </div>
    </div>
  )
}
