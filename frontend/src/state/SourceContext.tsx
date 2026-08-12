import { createContext, useContext, useState, type ReactNode } from 'react'
import { TRUSTED_SOURCES } from '../data/sources'
import { useToast } from './ToastContext'

const STORAGE_KEY = 'medivita:trusted-sources'
const defaultIds = TRUSTED_SOURCES.map((source) => source.id)

function readStoredSources(): string[] {
  try {
    const value = JSON.parse(localStorage.getItem(STORAGE_KEY) || 'null')
    if (Array.isArray(value)) {
      const valid = defaultIds.filter((id) => value.includes(id))
      if (valid.length) return valid
    }
  } catch { /* fall back safely */ }
  return defaultIds
}

interface SourceContextValue { enabledSourceIds: string[]; toggleSource: (id: string) => void; isEnabled: (id: string) => boolean }
const SourceContext = createContext<SourceContextValue | null>(null)

export function SourceProvider({ children }: { children: ReactNode }) {
  const [enabledSourceIds, setEnabledSourceIds] = useState(readStoredSources)
  const { notify } = useToast()
  const toggleSource = (id: string) => {
    const isRemoving = enabledSourceIds.includes(id)
    if (isRemoving && enabledSourceIds.length === 1) {
      notify('Keep at least one trusted source enabled.')
      return
    }
    const next = isRemoving
      ? enabledSourceIds.filter((item) => item !== id)
      : defaultIds.filter((item) => enabledSourceIds.includes(item) || item === id)
    localStorage.setItem(STORAGE_KEY, JSON.stringify(next))
    setEnabledSourceIds(next)
  }
  const value = { enabledSourceIds, toggleSource, isEnabled: (id: string) => enabledSourceIds.includes(id) }
  return <SourceContext.Provider value={value}>{children}</SourceContext.Provider>
}

export function useSources() {
  const context = useContext(SourceContext)
  if (!context) throw new Error('useSources must be used within SourceProvider')
  return context
}
