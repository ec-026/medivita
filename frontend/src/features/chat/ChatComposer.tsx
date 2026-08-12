import { Send, SlidersHorizontal } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useSources } from '../../state/SourceContext'

export function ChatComposer({ onSend, loading }: { onSend: (message: string) => void; loading: boolean }) {
  const [value, setValue] = useState('')
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const navigate = useNavigate()
  const { enabledSourceIds } = useSources()
  useEffect(() => {
    const textarea = textareaRef.current
    if (!textarea) return
    textarea.style.height = 'auto'
    textarea.style.height = `${Math.min(textarea.scrollHeight, 160)}px`
  }, [value])
  const submit = () => { const message = value.trim(); if (!message || loading) return; setValue(''); onSend(message) }
  return <div className="sticky bottom-0 z-20 bg-canvas/95 px-4 pb-4 pt-3 backdrop-blur-sm sm:px-6">
    <div className="mx-auto w-full max-w-[860px] rounded-[22px] border border-line bg-white p-2 shadow-float">
      <label htmlFor="chat-message" className="sr-only">Ask MediVita about a health topic</label>
      <textarea id="chat-message" ref={textareaRef} value={value} rows={1} maxLength={3000} disabled={loading} onChange={(event) => setValue(event.target.value)} onKeyDown={(event) => { if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); submit() } }} placeholder="Ask MediVita about a health topic..." className="max-h-[160px] min-h-10 w-full resize-none rounded-2xl border-0 bg-transparent px-3.5 py-2 text-[16px] leading-6 text-ink outline-none placeholder:text-faint disabled:opacity-60" />
      <div className="flex min-h-10 items-center justify-between gap-3 px-2 pb-1">
        <button type="button" onClick={() => navigate('/sources')} className="ghost-button gap-2 px-2 py-1.5 text-[13px] font-medium"><SlidersHorizontal size={15} /><span>{enabledSourceIds.length} trusted source{enabledSourceIds.length === 1 ? '' : 's'}</span></button>
        <button type="button" onClick={submit} disabled={!value.trim() || loading} aria-label="Send message" className="primary-button h-9 w-9 rounded-full px-0"><Send size={16} /></button>
      </div>
    </div>
    <p className="mx-auto mt-2 max-w-[860px] text-center text-[12px] leading-4 text-faint">Informational guidance only—not diagnosis or emergency care.</p>
  </div>
}
