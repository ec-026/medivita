import { AlertTriangle } from 'lucide-react'
import { BrandMark } from '../../components/ui/BrandMark'
import { SourceReferences } from '../../components/ui/SourceReferences'
import type { ChatResponse } from '../../types'
import { ResearchActivity } from '../research/ResearchActivity'

export function AssistantResponse({ response }: { response: ChatResponse; latest?: boolean }) {
  return <article className="pb-8">
    <header className="mb-3.5 flex items-center gap-3"><BrandMark className="h-8 w-8 shrink-0" /><div className="leading-none"><p className="text-[15px] font-semibold leading-5 text-ink">MediVita</p><p className="mt-0.5 text-[13px] leading-4 text-faint">{response.mode === 'demo' ? 'Demo response' : 'Researched response'}</p></div></header>
    {response.safety_notice && <div className="mb-5 flex gap-3 rounded-2xl bg-coral-pale p-4 text-[13px] leading-6 text-coral-dark"><AlertTriangle className="mt-0.5 shrink-0" size={17} /><p>{response.safety_notice}</p></div>}
    <ResearchActivity events={response.research_trace} summary={response.research_summary} />
    <div className="max-w-[760px] space-y-8">{response.sections.map((section) => <section key={section.title}><h3 className="mb-3 text-[18px] font-semibold tracking-[-.015em] text-ink">{section.title.replace('When to seek medical care', 'When to seek care')}</h3><p className="text-[17px] leading-[1.72] text-muted">{section.content}</p></section>)}</div>
    <section className="mt-9 max-w-[760px] border-t border-line-light pt-5"><h3 className="mb-3 text-[13px] font-semibold uppercase tracking-[.1em] text-muted">Sources</h3><SourceReferences sources={response.sources} /><p className="mt-3 text-[12px] leading-5 text-faint">Links are provided for further reading; listed organizations do not endorse MediVita.</p></section>
  </article>
}
