import { useEffect } from 'react'
import { useHistoryStore } from '../stores/historyStore'

export default function History() {
  const { entries, fetch, clear } = useHistoryStore()

  useEffect(() => { fetch() }, [])

  return (
    <div className="max-w-3xl">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-lg font-semibold">History</h2>
          <p className="text-sm text-gray-400">Last 50 transcriptions</p>
        </div>
        {entries.length > 0 && (
          <button
            onClick={clear}
            className="text-sm text-red-400 hover:text-red-300 transition-colors"
          >
            Clear history
          </button>
        )}
      </div>

      {entries.length === 0 && (
        <p className="text-gray-500 text-sm">No transcriptions yet.</p>
      )}

      <div className="space-y-3">
        {[...entries].reverse().map((entry, i) => (
          <div key={i} className="bg-gray-900 rounded-lg p-4 border border-gray-800">
            <div className="flex items-center gap-2 mb-3">
              <span className="text-xs text-gray-500">
                {new Date(entry.timestamp).toLocaleString()}
              </span>
              <span className="text-xs bg-gray-800 text-gray-300 px-2 py-0.5 rounded">
                {entry.app}
              </span>
              <span className="text-xs bg-blue-900 text-blue-300 px-2 py-0.5 rounded">
                {entry.tone}
              </span>
            </div>
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <p className="text-xs text-gray-500 mb-1 uppercase tracking-wide">Raw</p>
                <p className="text-gray-400 italic">{entry.raw}</p>
              </div>
              <div>
                <p className="text-xs text-gray-500 mb-1 uppercase tracking-wide">Polished</p>
                <p className="text-gray-100">{entry.polished}</p>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
