import { create } from 'zustand'

interface ToneMapping {
  tone: 'Formal' | 'Casual' | 'Terse' | 'Custom'
  custom_instruction: string
}

interface Settings {
  openai_api_key: string
  whisper_model: string
  tone_mappings: Record<string, ToneMapping>
  // WARNING: never log or persist this field — it contains a secret key
  history_enabled: boolean
}

interface SettingsStore {
  settings: Settings | null
  loading: boolean
  error: string | null
  fetch: () => Promise<void>
  update: (patch: Partial<Settings>) => Promise<void>
}

export const useSettingsStore = create<SettingsStore>((set, get) => ({
  settings: null,
  loading: false,
  error: null,
  fetch: async () => {
    set({ loading: true, error: null })
    try {
      const res = await fetch('/api/settings')
      if (!res.ok) throw new Error(`GET /api/settings failed: ${res.status}`)
      set({ settings: await res.json() })
    } catch (e) {
      set({ error: (e as Error).message })
    } finally {
      set({ loading: false })
    }
  },
  update: async (patch) => {
    set({ error: null })
    const res = await fetch('/api/settings', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(patch),
    })
    if (!res.ok) {
      set({ error: `POST /api/settings failed: ${res.status}` })
      return
    }
    await get().fetch()
  },
}))
