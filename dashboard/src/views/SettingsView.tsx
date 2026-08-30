import { useEffect, useState } from 'react'
import { useSettingsStore } from '../stores/settingsStore'

export default function SettingsView() {
  const { settings, fetch, update } = useSettingsStore()
  const [apiKey, setApiKey] = useState('')
  const [saved, setSaved] = useState(false)

  useEffect(() => { fetch() }, [])

  const handleSaveKey = async () => {
    if (!apiKey) return
    await update({ openai_api_key: apiKey })
    setApiKey('')
    setSaved(true)
    setTimeout(() => setSaved(false), 2000)
  }

  const handleModelChange = async (model: string) => {
    await update({ whisper_model: model })
  }

  if (!settings) return <div className="text-gray-400">Loading...</div>

  return (
    <div className="max-w-lg space-y-8">
      <h2 className="text-lg font-semibold">Settings</h2>

      {/* OpenAI API Key */}
      <div className="bg-gray-900 rounded-lg p-5 border border-gray-800">
        <h3 className="font-medium mb-1">OpenAI API Key</h3>
        <p className="text-xs text-gray-400 mb-4">
          Used for GPT-4o-mini intent rewriting. Stored locally — never sent anywhere else.
          {settings.openai_api_key ? (
            <span className="ml-2 text-green-400">✓ Key saved</span>
          ) : (
            <span className="ml-2 text-yellow-400">⚠ No key set</span>
          )}
        </p>
        <div className="flex gap-2">
          <input
            type="password"
            placeholder="sk-proj-…"
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
            className="flex-1 bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm text-gray-100 placeholder-gray-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
          <button
            onClick={handleSaveKey}
            disabled={!apiKey}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-500 disabled:opacity-40 rounded text-sm font-medium transition-colors"
          >
            {saved ? 'Saved ✓' : 'Save'}
          </button>
        </div>
      </div>

      {/* Whisper Model */}
      <div className="bg-gray-900 rounded-lg p-5 border border-gray-800">
        <h3 className="font-medium mb-1">Whisper Model</h3>
        <p className="text-xs text-gray-400 mb-4">
          Larger model = better accuracy, higher RAM usage. Restart the daemon after changing.
        </p>
        <div className="flex gap-3">
          {['small.en', 'medium.en'].map((model) => (
            <button
              key={model}
              onClick={() => handleModelChange(model)}
              className={`px-4 py-2 rounded text-sm font-medium border transition-colors ${
                settings.whisper_model === model
                  ? 'border-blue-500 bg-blue-900 text-blue-200'
                  : 'border-gray-700 bg-gray-800 text-gray-300 hover:border-gray-500'
              }`}
            >
              {model}
              {model === 'small.en' && <span className="text-xs text-gray-400 ml-1">(~240MB)</span>}
              {model === 'medium.en' && <span className="text-xs text-gray-400 ml-1">(~1.5GB)</span>}
            </button>
          ))}
        </div>
      </div>

      {/* Hotkey (read-only) */}
      <div className="bg-gray-900 rounded-lg p-5 border border-gray-800">
        <h3 className="font-medium mb-1">Hotkey</h3>
        <p className="text-xs text-gray-400 mb-3">Hold to record, release to transcribe.</p>
        <kbd className="px-3 py-1.5 bg-gray-800 border border-gray-600 rounded text-sm font-mono text-gray-200">
          Right Option ⌥
        </kbd>
      </div>
    </div>
  )
}
