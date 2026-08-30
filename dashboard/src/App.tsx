import { useState } from 'react'
import ToneMapper from './views/ToneMapper'
import History from './views/History'
import SettingsView from './views/SettingsView'

type Tab = 'tones' | 'history' | 'settings'

export default function App() {
  const [tab, setTab] = useState<Tab>('tones')

  const tabs: { id: Tab; label: string }[] = [
    { id: 'tones', label: 'Tone Mapper' },
    { id: 'history', label: 'History' },
    { id: 'settings', label: 'Settings' },
  ]

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100 flex flex-col">
      <header className="bg-gray-900 border-b border-gray-800 px-6 py-4 flex items-center gap-3">
        <span className="text-xl">🎤</span>
        <h1 className="text-lg font-semibold">IntenType</h1>
      </header>

      <nav className="bg-gray-900 border-b border-gray-800 px-6 flex gap-1">
        {tabs.map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
              tab === t.id
                ? 'border-blue-500 text-blue-400'
                : 'border-transparent text-gray-400 hover:text-gray-200'
            }`}
          >
            {t.label}
          </button>
        ))}
      </nav>

      <main className="flex-1 p-6">
        {tab === 'tones' && <ToneMapper />}
        {tab === 'history' && <History />}
        {tab === 'settings' && <SettingsView />}
      </main>
    </div>
  )
}
