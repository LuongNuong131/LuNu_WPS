export interface HistoryItem {
  id: string
  name: string
  tool: string
  output: string
  completedAt: string
}

const STORAGE_KEY = 'officeflow-history'

export function readHistory(): HistoryItem[] {
  try {
    const value = JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]')
    return Array.isArray(value) ? value : []
  } catch {
    return []
  }
}

export function saveHistory(item: HistoryItem) {
  const next = [item, ...readHistory().filter((entry) => entry.id !== item.id)].slice(0, 25)
  localStorage.setItem(STORAGE_KEY, JSON.stringify(next))
}
