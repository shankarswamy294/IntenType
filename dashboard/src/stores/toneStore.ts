import { create } from 'zustand'

// Maps tone name (e.g. "Formal") → instruction string
// Different from settingsStore.tone_mappings which maps app name → ToneMapping object
interface ToneStore {
  tones: Record<string, string>
  loading: boolean
  error: string | null
  fetch: () => Promise<void>
}

export const useToneStore = create<ToneStore>((set) => ({
  tones: {},
  loading: false,
  error: null,
  fetch: async () => {
    set({ loading: true, error: null })
    try {
      const res = await fetch('/api/tones')
      if (!res.ok) throw new Error(`GET /api/tones failed: ${res.status}`)
      set({ tones: await res.json() })
    } catch (e) {
      set({ error: (e as Error).message })
    } finally {
      set({ loading: false })
    }
  },
}))
