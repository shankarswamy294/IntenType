import { create } from 'zustand'

interface ToneStore {
  tones: Record<string, string>
  fetch: () => Promise<void>
}

export const useToneStore = create<ToneStore>((set) => ({
  tones: {},
  fetch: async () => {
    const res = await fetch('/api/tones')
    set({ tones: await res.json() })
  },
}))
