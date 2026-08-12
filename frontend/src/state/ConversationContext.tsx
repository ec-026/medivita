import { createContext, useContext, useState, type ReactNode } from 'react'
import type { ChatMessage, Conversation } from '../types'

const STORAGE_KEY = 'medivita:conversations'
const ACTIVE_KEY = 'medivita:active-conversation'

function loadConversations(): Conversation[] {
  try {
    const stored = localStorage.getItem(STORAGE_KEY)
    if (stored) { const data = JSON.parse(stored); return Array.isArray(data) ? data : [] }
  } catch { /* use curated examples */ }
  const now = new Date()
  return ['Understanding migraines', 'Vitamin D levels', 'Seasonal allergies', 'Understanding insulin resistance'].map((title, index) => ({
    id: `example-${index}`, title, updatedAt: new Date(now.getTime() - index * 86400000).toISOString(),
    messages: [{ id: `example-message-${index}`, role: 'user' as const, content: title, createdAt: now.toISOString() }],
  }))
}

interface ConversationContextValue {
  conversations: Conversation[]
  activeConversation: Conversation | null
  newConversation: () => void
  selectConversation: (id: string) => void
  addMessage: (message: ChatMessage, conversationId?: string) => string
  renameConversation: (id: string, title: string) => void
  deleteConversation: (id: string) => void
}
const ConversationContext = createContext<ConversationContextValue | null>(null)

export function ConversationProvider({ children }: { children: ReactNode }) {
  const [conversations, setConversations] = useState(loadConversations)
  const [activeId, setActiveId] = useState<string | null>(() => localStorage.getItem(ACTIVE_KEY))
  const activeConversation = conversations.find((conversation) => conversation.id === activeId) || null

  const newConversation = () => { setActiveId(null); localStorage.removeItem(ACTIVE_KEY) }
  const selectConversation = (id: string) => { setActiveId(id); localStorage.setItem(ACTIVE_KEY, id) }
  const addMessage = (message: ChatMessage, conversationId?: string) => {
    const targetId = conversationId || activeId || crypto.randomUUID()
    setConversations((current) => {
      const existing = current.find((conversation) => conversation.id === targetId)
      const next = existing
        ? current.map((conversation) => conversation.id === targetId ? { ...conversation, messages: [...conversation.messages, message], updatedAt: message.createdAt } : conversation)
        : [{ id: targetId, title: message.content.slice(0, 42), updatedAt: message.createdAt, messages: [message] }, ...current]
      localStorage.setItem(STORAGE_KEY, JSON.stringify(next.slice(0, 12)))
      return next
    })
    setActiveId(targetId)
    localStorage.setItem(ACTIVE_KEY, targetId)
    return targetId
  }
  const renameConversation = (id: string, title: string) => {
    const nextTitle = title.trim().slice(0, 100)
    if (!nextTitle) return
    setConversations((current) => {
      const next = current.map((conversation) => conversation.id === id ? { ...conversation, title: nextTitle } : conversation)
      localStorage.setItem(STORAGE_KEY, JSON.stringify(next))
      return next
    })
  }
  const deleteConversation = (id: string) => {
    setConversations((current) => {
      const next = current.filter((conversation) => conversation.id !== id)
      localStorage.setItem(STORAGE_KEY, JSON.stringify(next))
      return next
    })
    if (activeId === id) {
      setActiveId(null)
      localStorage.removeItem(ACTIVE_KEY)
    }
  }
  const value = { conversations, activeConversation, newConversation, selectConversation, addMessage, renameConversation, deleteConversation }
  return <ConversationContext.Provider value={value}>{children}</ConversationContext.Provider>
}

export function useConversations() {
  const context = useContext(ConversationContext)
  if (!context) throw new Error('useConversations must be used within ConversationProvider')
  return context
}
