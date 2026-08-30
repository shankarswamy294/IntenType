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
  fetch: () => Promise<void>
  clear: () => Promise<void>
}

export const useHistoryStore = create<HistoryStore>((set) => ({
  entries: [],
  fetch: async () => {
    const res = await fetch('/api/history')
    set({ entries: await res.json() })
  },
  clear: async () => {
    await fetch('/api/history/clear', { method: 'POST' })
    set({ entries: [] })
  },
}))
