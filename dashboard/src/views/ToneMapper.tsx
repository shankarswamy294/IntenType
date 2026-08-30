import { useEffect } from 'react'
import { useSettingsStore } from '../stores/settingsStore'
import { useHistoryStore } from '../stores/historyStore'
import { useToneStore } from '../stores/toneStore'

const TONE_OPTIONS = ['Formal', 'Casual', 'Terse', 'Custom'] as const
type ToneName = typeof TONE_OPTIONS[number]

export default function ToneMapper() {
  const { settings, fetch: fetchSettings, update } = useSettingsStore()
  const { entries, fetch: fetchHistory } = useHistoryStore()
  const { tones, fetch: fetchTones } = useToneStore()

  useEffect(() => {
    fetchSettings()
    fetchHistory()
    fetchTones()
  }, [])

  const seenApps = Array.from(
    new Set([
      ...Object.keys(settings?.tone_mappings ?? {}),
      ...entries.map((e) => e.app),
    ])
  ).sort()

  const getMapping = (app: string) =>
    settings?.tone_mappings?.[app] ?? { tone: 'Casual', custom_instruction: '' }

  const setTone = async (app: string, tone: ToneName) => {
    const current = getMapping(app)
    await update({
      tone_mappings: {
        ...settings?.tone_mappings,
        [app]: { ...current, tone },
      },
    })
  }

  const setCustomInstruction = async (app: string, custom_instruction: string) => {
    const current = getMapping(app)
    await update({
      tone_mappings: {
        ...settings?.tone_mappings,
        [app]: { ...current, custom_instruction },
      },
    })
  }

  if (!settings) return <div className="text-gray-400">Loading...</div>

  return (
    <div className="max-w-2xl">
      <h2 className="text-lg font-semibold mb-1">Tone Mapper</h2>
      <p className="text-sm text-gray-400 mb-6">
        Set the writing tone IntenType uses per app. Apps appear here once they've been used.
      </p>

      {seenApps.length === 0 && (
        <p className="text-gray-500 text-sm">
          No apps detected yet. Use the hotkey in any app to see it here.
        </p>
      )}

      <div className="space-y-3">
        {seenApps.map((app) => {
          const mapping = getMapping(app)
          return (
            <div key={app} className="bg-gray-900 rounded-lg p-4 border border-gray-800">
              <div className="flex items-center justify-between gap-4">
                <span className="font-medium text-gray-100 w-40 truncate">{app}</span>
                <select
                  value={mapping.tone}
                  onChange={(e) => setTone(app, e.target.value as ToneName)}
                  className="bg-gray-800 border border-gray-700 rounded px-3 py-1.5 text-sm text-gray-100 focus:outline-none focus:ring-1 focus:ring-blue-500"
                >
                  {TONE_OPTIONS.map((t) => (
                    <option key={t} value={t}>{t}</option>
                  ))}
                </select>
              </div>

              {mapping.tone === 'Custom' && (
                <input
                  type="text"
                  placeholder="Custom tone instruction…"
                  value={mapping.custom_instruction}
                  onChange={(e) => setCustomInstruction(app, e.target.value)}
                  className="mt-3 w-full bg-gray-800 border border-gray-700 rounded px-3 py-1.5 text-sm text-gray-100 placeholder-gray-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                />
              )}

              {mapping.tone !== 'Custom' && tones[mapping.tone] && (
                <p className="mt-2 text-xs text-gray-500">{tones[mapping.tone]}</p>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
