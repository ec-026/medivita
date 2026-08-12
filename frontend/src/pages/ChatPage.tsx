import { Activity, BookOpen, HeartPulse, Pill } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { SUGGESTIONS } from '../data/sources'
import { AssistantResponse } from '../features/chat/AssistantResponse'
import { ChatComposer } from '../features/chat/ChatComposer'
import { ResponseLoading } from '../features/chat/ResponseLoading'
import { mergeTraceEvent } from '../features/research/mergeTrace'
import { api } from '../services/api'
import { useConversations } from '../state/ConversationContext'
import { useSources } from '../state/SourceContext'
import { useToast } from '../state/ToastContext'
import type { ChatMessage, ResearchTraceEvent } from '../types'

const ICONS = { activity: Activity, pill: Pill, book: BookOpen, heart: HeartPulse }

export function ChatPage() {
  const { activeConversation, addMessage } = useConversations()
  const { enabledSourceIds } = useSources()
  const { notify } = useToast()
  const [loading, setLoading] = useState(false)
  const [liveTrace, setLiveTrace] = useState<ResearchTraceEvent[]>([])
  const endRef = useRef<HTMLDivElement>(null)
  const messages = activeConversation?.messages || []
  useEffect(() => { endRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [messages.length, loading])

  const sendMessage = async (content: string) => {
    if (loading) return
    const createdAt = new Date().toISOString()
    const userMessage: ChatMessage = { id: crypto.randomUUID(), role: 'user', content, createdAt }
    const conversationId = addMessage(userMessage)
    setLiveTrace([]); setLoading(true)
    try {
      const history = messages.slice(-8).map((message) => ({ role: message.role, content: message.content }))
      let collectedTrace: ResearchTraceEvent[] = []
      const response = await api.chatWithTrace(content, enabledSourceIds, history, (event) => {
        collectedTrace = mergeTraceEvent(collectedTrace, event); setLiveTrace(collectedTrace)
      })
      if (!response.research_trace && collectedTrace.length > 0) response.research_trace = collectedTrace
      addMessage({ id: crypto.randomUUID(), role: 'assistant', content: response.answer, response, createdAt: new Date().toISOString() }, conversationId)
    } catch (error) {
      notify(error instanceof Error ? error.message : "MediVita couldn't complete that response. Please try again.", 'error')
    } finally { setLoading(false) }
  }

  const empty = messages.length === 0
  return <div className="flex min-h-[100dvh] flex-col">
    <div className="flex-1 px-4 pt-7 sm:px-6">
      {empty ? <div className="mx-auto flex min-h-[62vh] max-w-[760px] flex-col justify-center py-10">
        <div className="text-center"><span className="mx-auto grid h-12 w-12 place-items-center rounded-2xl bg-mint text-brand-dark shadow-soft"><HeartPulse size={22} /></span><h1 className="mt-5 text-[27px] font-semibold tracking-[-.035em] text-ink sm:text-[32px]">How can I help you explore your health question?</h1><p className="mx-auto mt-3 max-w-lg text-[14px] leading-6 text-muted">I can research information from the trusted health sources you choose.</p></div>
        <div className="mx-auto mt-8 flex max-w-2xl flex-wrap justify-center gap-2.5">{SUGGESTIONS.map((suggestion) => { const Icon = ICONS[suggestion.icon]; return <button type="button" key={suggestion.title} onClick={() => sendMessage(suggestion.prompt)} className="focus-ring group inline-flex items-center gap-2 rounded-full border border-line bg-white px-3.5 py-2.5 text-left text-[12px] font-medium text-muted shadow-soft transition duration-200 hover:border-mint hover:bg-mint-pale hover:text-ink"><Icon size={14} className="text-brand" /><span>{suggestion.title}</span></button> })}</div>
      </div> : <div className="mx-auto w-full max-w-[860px] space-y-8 pb-28">{messages.map((message) => message.role === 'user' ? <div key={message.id} className="flex justify-end"><div className="max-w-[88%] rounded-[18px] rounded-br-md bg-peach-pale px-4 py-3 text-[16px] leading-7 text-ink sm:max-w-[72%]">{message.content}</div></div> : message.response ? <AssistantResponse key={message.id} response={message.response} /> : null)}{loading && <ResponseLoading trace={liveTrace} />}<div ref={endRef} /></div>}
    </div>
    <ChatComposer onSend={sendMessage} loading={loading} />
  </div>
}
