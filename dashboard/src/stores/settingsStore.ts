import { create } from 'zustand'

interface ToneMapping {
  tone: 'Formal' | 'Casual' | 'Terse' | 'Custom'
  custom_instruction: string
}

interface Settings {
  openai_api_key: string
  whisper_model: string
  tone_mappings: Record<string, ToneMapping>
  history_enabled: boolean
}

interface SettingsStore {
  settings: Settings | null
  fetch: () => Promise<void>
  update: (patch: Partial<Settings>) => Promise<void>
}

export const useSettingsStore = create<SettingsStore>((set, get) => ({
  settings: null,
  fetch: async () => {
    const res = await fetch('/api/settings')
    set({ settings: await res.json() })
  },
  update: async (patch) => {
    await fetch('/api/settings', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(patch),
    })
    await get().fetch()
  },
}))
