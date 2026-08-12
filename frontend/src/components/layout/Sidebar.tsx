import {
  Activity,
  Ellipsis,
  ExternalLink,
  MessageSquare,
  Newspaper,
  PanelLeftClose,
  PanelLeftOpen,
  Pencil,
  Plus,
  ShieldCheck,
  Trash2,
} from 'lucide-react'
import { useEffect, useRef, useState, type KeyboardEvent as ReactKeyboardEvent } from 'react'
import { createPortal } from 'react-dom'
import { NavLink, useNavigate } from 'react-router-dom'
import { useConversations } from '../../state/ConversationContext'
import type { Conversation } from '../../types'
import { BrandMark } from '../ui/BrandMark'

const NAVIGATION = [
  { to: '/chat', label: 'Chat', icon: MessageSquare },
  { to: '/health-check', label: 'Health Check', icon: Activity },
  { to: '/news', label: 'Health News', icon: Newspaper },
  { to: '/sources', label: 'Trusted Sources', icon: ShieldCheck },
]

interface MenuState { conversation: Conversation; top: number; left: number }
interface RenameState { id: string; value: string }

export function Sidebar({
  collapsed = false,
  onToggle,
  onNavigate,
  mobile = false,
}: {
  collapsed?: boolean
  onToggle?: () => void
  onNavigate?: () => void
  mobile?: boolean
}) {
  const navigate = useNavigate()
  const { conversations, newConversation, selectConversation, activeConversation, renameConversation, deleteConversation } = useConversations()
  const [menu, setMenu] = useState<MenuState | null>(null)
  const [renaming, setRenaming] = useState<RenameState | null>(null)
  const [pendingDelete, setPendingDelete] = useState<Conversation | null>(null)
  const compact = collapsed && !mobile
  const menuRef = useRef<HTMLDivElement>(null)
  const firstMenuItemRef = useRef<HTMLButtonElement>(null)
  const renameRef = useRef<HTMLInputElement>(null)
  const newConversationRef = useRef<HTMLButtonElement>(null)
  const cancelDeleteRef = useRef<HTMLButtonElement>(null)
  const optionRefs = useRef(new Map<string, HTMLButtonElement>())
  const renameCancelled = useRef(false)
  const renamingId = renaming?.id

  const startNew = () => { newConversation(); navigate('/chat'); onNavigate?.() }
  const select = (id: string) => { selectConversation(id); navigate('/chat'); onNavigate?.() }
  const closeMenu = (restoreFocus = true) => {
    const id = menu?.conversation.id
    setMenu(null)
    if (restoreFocus && id) window.setTimeout(() => optionRefs.current.get(id)?.focus(), 0)
  }

  useEffect(() => {
    if (!menu) return
    firstMenuItemRef.current?.focus()
    const restoreMenuFocus = () => {
      const id = menu.conversation.id
      setMenu(null)
      window.setTimeout(() => optionRefs.current.get(id)?.focus(), 0)
    }
    const onPointerDown = (event: PointerEvent) => {
      const target = event.target as Node
      if (menuRef.current?.contains(target) || optionRefs.current.get(menu.conversation.id)?.contains(target)) return
      restoreMenuFocus()
    }
    const onKeyDown = (event: KeyboardEvent) => { if (event.key === 'Escape') restoreMenuFocus() }
    document.addEventListener('pointerdown', onPointerDown)
    document.addEventListener('keydown', onKeyDown)
    return () => { document.removeEventListener('pointerdown', onPointerDown); document.removeEventListener('keydown', onKeyDown) }
  }, [menu])

  useEffect(() => {
    if (!renamingId) return
    renameCancelled.current = false
    renameRef.current?.focus()
    renameRef.current?.select()
  }, [renamingId])

  useEffect(() => {
    if (!pendingDelete) return
    cancelDeleteRef.current?.focus()
    const restoreDeleteFocus = () => {
      const id = pendingDelete.id
      setPendingDelete(null)
      window.setTimeout(() => (optionRefs.current.get(id) || newConversationRef.current)?.focus(), 0)
    }
    const onKeyDown = (event: KeyboardEvent) => { if (event.key === 'Escape') restoreDeleteFocus() }
    document.addEventListener('keydown', onKeyDown)
    return () => document.removeEventListener('keydown', onKeyDown)
  }, [pendingDelete])

  const openMenu = (conversation: Conversation, trigger: HTMLButtonElement) => {
    if (menu?.conversation.id === conversation.id) { closeMenu(); return }
    const rect = trigger.getBoundingClientRect()
    const menuWidth = 148
    const menuHeight = 88
    setMenu({
      conversation,
      top: rect.bottom + menuHeight + 8 > window.innerHeight ? Math.max(8, rect.top - menuHeight - 4) : rect.bottom + 4,
      left: Math.min(Math.max(8, rect.right - menuWidth), window.innerWidth - menuWidth - 8),
    })
  }
  const startRename = (conversation: Conversation) => {
    closeMenu(false)
    setRenaming({ id: conversation.id, value: conversation.title })
  }
  const saveRename = () => {
    if (!renaming || renameCancelled.current) { renameCancelled.current = false; return }
    renameConversation(renaming.id, renaming.value)
    const id = renaming.id
    setRenaming(null)
    window.setTimeout(() => optionRefs.current.get(id)?.focus(), 0)
  }
  const handleRenameKey = (event: ReactKeyboardEvent<HTMLInputElement>) => {
    if (event.key === 'Enter') { event.preventDefault(); saveRename() }
    if (event.key === 'Escape') {
      event.preventDefault()
      renameCancelled.current = true
      const id = renaming?.id
      setRenaming(null)
      if (id) window.setTimeout(() => optionRefs.current.get(id)?.focus(), 0)
    }
  }
  const confirmDelete = () => {
    if (!pendingDelete) return
    const deletingActive = activeConversation?.id === pendingDelete.id
    deleteConversation(pendingDelete.id)
    setPendingDelete(null)
    window.setTimeout(() => newConversationRef.current?.focus(), 0)
    if (deletingActive) onNavigate?.()
  }
  const cancelDelete = () => {
    const id = pendingDelete?.id
    setPendingDelete(null)
    if (id) window.setTimeout(() => (optionRefs.current.get(id) || newConversationRef.current)?.focus(), 0)
  }

  return <div className={`flex h-full min-h-0 flex-col bg-surface ${compact ? 'items-center px-2' : 'px-3'} pb-4 pt-4`}>
    <div className={`flex h-11 w-full shrink-0 items-center ${compact ? 'justify-center' : 'gap-2.5 px-1'}`}>
      <BrandMark className="h-9 w-9 shrink-0" />
      {!compact && <div className="min-w-0 flex-1"><p className="text-[17px] font-semibold leading-5 tracking-[-.025em] text-ink">MediVita</p><p className="text-[13px] leading-4 text-muted">AI Health Assistant</p></div>}
      {!mobile && !compact && <button type="button" onClick={onToggle} aria-label="Collapse navigation sidebar" title="Collapse sidebar" className="ghost-button h-10 w-10 shrink-0"><PanelLeftClose size={18} /></button>}
    </div>

    <button ref={newConversationRef} type="button" onClick={startNew} aria-label="New conversation" title={compact ? 'New conversation' : undefined} className={`primary-button mt-5 h-11 shrink-0 ${compact ? 'w-11 px-0' : 'w-full gap-2 px-3 text-[15px]'}`}><Plus size={18} />{!compact && 'New conversation'}</button>

    <nav className={`mt-5 w-full shrink-0 space-y-1 ${compact ? 'flex flex-col items-center' : ''}`} aria-label="Primary navigation">
      {NAVIGATION.map(({ to, label, icon: Icon }) => <NavLink
        key={to}
        to={to}
        onClick={onNavigate}
        aria-label={compact ? label : undefined}
        title={compact ? label : undefined}
        className={({ isActive }) => `focus-ring flex h-11 items-center rounded-xl text-[15px] font-medium transition duration-200 ${compact ? 'w-11 justify-center' : 'w-full gap-3 px-3'} ${isActive ? 'bg-mint-pale text-brand-dark' : 'text-muted hover:bg-surface-muted hover:text-ink'}`}
      ><Icon size={19} strokeWidth={1.8} /><span className={compact ? 'sr-only' : ''}>{label}</span></NavLink>)}
    </nav>

    {!compact && <>
      <div className="mx-2 my-5 w-[calc(100%-16px)] shrink-0 border-t border-line-light" />
      <div className="flex min-h-0 w-full flex-1 flex-col" data-testid="conversation-region">
        <p className="shrink-0 px-3 text-[11px] font-semibold uppercase tracking-[.13em] text-faint">Recent conversations</p>
        <div className="sidebar-scroll mt-2 min-h-0 flex-1 space-y-0.5 overflow-y-auto pr-1" data-testid="conversation-scroll">
          {conversations.length === 0 ? <p className="px-3 py-4 text-[14px] text-muted">No conversations yet</p> : conversations.map((conversation) => {
            const editing = renaming?.id === conversation.id
            const selected = activeConversation?.id === conversation.id
            return <div key={conversation.id} className={`group grid h-[56px] grid-cols-[minmax(0,1fr)_36px] items-center rounded-lg transition duration-200 hover:bg-surface-muted ${selected ? 'bg-lime-pale/70' : ''}`}>
              {editing ? <input
                ref={renameRef}
                aria-label={`Rename ${conversation.title}`}
                value={renaming.value}
                maxLength={100}
                onChange={(event) => setRenaming({ id: conversation.id, value: event.target.value })}
                onKeyDown={handleRenameKey}
                onBlur={saveRename}
                className="focus-ring col-span-2 mx-2 h-9 min-w-0 rounded-lg border border-mint bg-white px-2.5 text-[15px] text-ink"
              /> : <>
                <button type="button" onClick={() => select(conversation.id)} className="focus-ring min-w-0 rounded-lg px-3 py-2 text-left">
                  <span className="block truncate text-[15px] font-medium leading-5 text-ink">{conversation.title}</span>
                  <span className="block text-[12px] leading-4 text-faint">{formatRelative(conversation.updatedAt)}</span>
                </button>
                <button
                  ref={(node) => { if (node) optionRefs.current.set(conversation.id, node); else optionRefs.current.delete(conversation.id) }}
                  type="button"
                  aria-label={`Conversation options for ${conversation.title}`}
                  aria-haspopup="menu"
                  aria-expanded={menu?.conversation.id === conversation.id}
                  onClick={(event) => openMenu(conversation, event.currentTarget)}
                  className={`ghost-button h-9 w-9 rounded-lg md:opacity-0 md:group-focus-within:opacity-100 md:group-hover:opacity-100 ${selected || menu?.conversation.id === conversation.id ? 'md:opacity-70' : ''}`}
                ><Ellipsis size={18} /></button>
              </>}
            </div>
          })}
        </div>
      </div>
      <div className="mx-1 mt-3 shrink-0 rounded-xl bg-lime-pale p-3" data-testid="privacy-footer"><p className="text-[13px] font-semibold leading-5 text-lime-dark">Private by design</p><p className="text-[12px] leading-4 text-muted">Conversations stay in this browser.</p></div>
      <a
        href="https://tejas-singh.pages.dev/"
        target="_blank"
        rel="noopener noreferrer"
        aria-label="Visit Tejas Singh's portfolio"
        title="View Tejas Singh's portfolio"
        className="focus-ring mx-1 mt-1.5 flex min-h-9 shrink-0 items-center justify-center gap-1.5 rounded-lg px-2 text-[13px] text-muted transition hover:bg-surface-muted hover:text-brand-dark hover:underline"
      >
        <span>Built by <span className="font-semibold text-ink">Tejas Singh</span></span>
        <ExternalLink size={13} aria-hidden="true" />
      </a>
    </>}

    {compact && <button type="button" onClick={onToggle} aria-label="Expand navigation sidebar" title="Expand sidebar" className="ghost-button mt-auto h-11 w-11"><PanelLeftOpen size={18} /></button>}

    {menu && createPortal(<div ref={menuRef} role="menu" aria-label={`Actions for ${menu.conversation.title}`} style={{ top: menu.top, left: menu.left }} className="fixed z-[100] w-[148px] rounded-xl border border-line bg-white p-1.5 shadow-float">
      <button ref={firstMenuItemRef} type="button" role="menuitem" onClick={() => startRename(menu.conversation)} className="focus-ring flex h-9 w-full items-center gap-2 rounded-lg px-2.5 text-left text-[14px] font-medium text-ink hover:bg-surface-muted"><Pencil size={15} />Rename</button>
      <button type="button" role="menuitem" onClick={() => { const conversation = menu.conversation; closeMenu(false); setPendingDelete(conversation) }} className="focus-ring flex h-9 w-full items-center gap-2 rounded-lg px-2.5 text-left text-[14px] font-medium text-coral-dark hover:bg-coral-pale"><Trash2 size={15} />Delete</button>
    </div>, document.body)}

    {pendingDelete && createPortal(<div className="fixed inset-0 z-[110] grid place-items-center bg-stone-950/25 px-4 backdrop-blur-[2px]" onMouseDown={(event) => { if (event.target === event.currentTarget) cancelDelete() }}>
      <div role="dialog" aria-modal="true" aria-labelledby="delete-conversation-title" aria-describedby="delete-conversation-description" className="w-full max-w-sm rounded-[18px] border border-line bg-white p-5 shadow-float">
        <h2 id="delete-conversation-title" className="text-[17px] font-semibold text-ink">Delete conversation?</h2>
        <p id="delete-conversation-description" className="mt-2 text-[14px] leading-6 text-muted">&ldquo;{pendingDelete.title}&rdquo; will be removed from this browser.</p>
        <div className="mt-5 flex justify-end gap-2">
          <button ref={cancelDeleteRef} type="button" onClick={cancelDelete} className="ghost-button h-10 px-3 text-[14px] font-semibold">Cancel</button>
          <button type="button" onClick={confirmDelete} className="focus-ring inline-flex h-10 items-center justify-center rounded-xl bg-coral px-4 text-[14px] font-semibold text-coral-dark transition hover:bg-coral/80">Delete</button>
        </div>
      </div>
    </div>, document.body)}
  </div>
}

function formatRelative(value: string) {
  const days = Math.floor((Date.now() - new Date(value).getTime()) / 86400000)
  return days <= 0 ? 'Today' : days === 1 ? 'Yesterday' : `${days} days ago`
}
