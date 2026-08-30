import { create } from 'zustand'

export interface HistoryEntry {
  timestamp: string
  app: string
  tone: string
  raw: string
  polished: string
}

interface HistoryStore {
  entries: HistoryEntry[]
  loading: boolean
  error: string | null
  fetch: () => Promise<void>
  clear: () => Promise<void>
}

export const useHistoryStore = create<HistoryStore>((set) => ({
  entries: [],
  loading: false,
  error: null,
  fetch: async () => {
    set({ loading: true, error: null })
    try {
      const res = await fetch('/api/history')
      if (!res.ok) throw new Error(`GET /api/history failed: ${res.status}`)
      set({ entries: await res.json() })
    } catch (e) {
      set({ error: (e as Error).message })
    } finally {
      set({ loading: false })
    }
  },
  clear: async () => {
    const res = await fetch('/api/history/clear', { method: 'POST' })
    if (!res.ok) return
    set({ entries: [] })
  },
}))
