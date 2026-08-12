import { Check, ChevronDown, Circle, LoaderCircle } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import type { ResearchSummary, ResearchTraceEvent } from '../../types/research'
import { ResearchTraceItem } from './ResearchTraceItem'

export function ResearchActivity({ events, summary, running = false, initiallyExpanded = false }: {
  events?: ResearchTraceEvent[]
  summary?: ResearchSummary
  running?: boolean
  initiallyExpanded?: boolean
}) {
  const normalized = useMemo(() => events || [], [events])
  const [detailsOpen, setDetailsOpen] = useState(running || initiallyExpanded)
  const [technicalOpen, setTechnicalOpen] = useState(false)
  useEffect(() => { if (running) setDetailsOpen(true) }, [running])
  if (normalized.length === 0) return null

  const demo = summary?.rounds === 0 || normalized.some((event) => event.label === 'Demo mode')
  const sourceCount = new Set(normalized.filter((event) => event.stage === 'search' && event.status === 'completed').map((event) => event.source_id).filter(Boolean)).size
  const headline = demo ? 'Demo response · no external research' : running ? runningLabel(normalized) : `Research complete${sourceCount ? ` · ${sourceCount} trusted source${sourceCount === 1 ? '' : 's'}` : ''}`

  return <section className="my-4 min-w-0" aria-label="Research activity">
    <button type="button" aria-expanded={detailsOpen} aria-controls={`research-details-${normalized[0].id}`} onClick={() => setDetailsOpen((value) => !value)} className="focus-ring group flex min-h-9 max-w-full items-center gap-2 rounded-lg py-1.5 pr-1 text-left">
      <span className={`grid h-5 w-5 shrink-0 place-items-center rounded-full ${demo ? 'bg-peach-pale text-peach-dark' : 'bg-mint-pale text-brand'}`}>{running ? <LoaderCircle size={12} className="animate-spin motion-reduce:animate-none" /> : <Check size={12} strokeWidth={2.4} />}</span>
      <span className="min-w-0 truncate text-[14px] font-medium text-muted" aria-live="polite">{headline}</span>
      <span className="inline-flex shrink-0 items-center gap-0.5 text-[13px] font-semibold text-faint transition-colors group-hover:text-ink">{detailsOpen ? 'Hide' : 'Details'}<ChevronDown size={14} className={`transition-transform duration-200 ${detailsOpen ? 'rotate-180' : ''}`} /></span>
    </button>

    {detailsOpen && <div id={`research-details-${normalized[0].id}`} className="ml-2.5 mt-2 border-l border-mint pl-4">
      {demo ? <p className="py-1 text-[14px] leading-6 text-muted">This response uses MediVita’s deterministic demo content. No search or AI provider was called.</p> : <FriendlyDetails events={normalized} summary={summary} running={running} />}
      {!demo && <div className="mt-3 border-t border-line-light pt-2">
        <button type="button" aria-expanded={technicalOpen} onClick={() => setTechnicalOpen((value) => !value)} className="focus-ring inline-flex min-h-8 items-center gap-1.5 rounded-lg py-1 text-[12px] font-semibold uppercase tracking-[.09em] text-faint hover:text-ink">Details <ChevronDown size={13} className={`transition-transform ${technicalOpen ? 'rotate-180' : ''}`} /></button>
        {technicalOpen && <div className="mt-2 rounded-xl bg-surface-muted px-3 py-2"><p className="mb-1 text-[12px] leading-5 text-faint">Operational metadata only—never private model reasoning or raw evidence.</p><ol className="divide-y divide-line">{normalized.map((event) => <ResearchTraceItem key={event.id} event={event} />)}</ol></div>}
      </div>}
    </div>}
  </section>
}

function FriendlyDetails({ events, summary, running }: { events: ResearchTraceEvent[]; summary?: ResearchSummary; running: boolean }) {
  const searches = events.filter((event) => event.stage === 'search' && event.status !== 'warning')
  const hasSecondRound = events.some((event) => (event.round || 1) > 1)
  const hasReading = events.some((event) => event.stage === 'page_retrieval' || event.stage === 'evidence')
  const evidenceCount = [...events].reverse().find((event) => event.evidence_count !== undefined)?.evidence_count
  const hasGeneration = events.some((event) => event.stage === 'generation')
  const generationRunning = events.some((event) => event.stage === 'generation' && event.status === 'running')
  const citationCount = summary?.citation_count ?? [...events].reverse().find((event) => event.citation_count !== undefined)?.citation_count
  return <div className="space-y-3 py-1">
    <FriendlyStep done label="Safety screening complete" />
    {searches.length > 0 && <div><FriendlyStep done={!searches.some((event) => event.status === 'running')} active={searches.some((event) => event.status === 'running')} label={hasSecondRound ? 'Looking for a little more information' : 'Searching trusted health sources'} /><div className="ml-6 mt-1.5 space-y-2">{searches.map((event) => <div key={event.id} className="min-w-0 text-[13px] leading-5 text-muted"><p><span className="font-semibold text-ink">{event.source_name || 'Trusted source'}</span>{event.result_count !== undefined ? ` · ${event.result_count} result${event.result_count === 1 ? '' : 's'}` : ''}</p>{event.query && <p className="mt-0.5 break-words text-faint">Searched: “{friendlyQuery(event.query)}”</p>}</div>)}</div></div>}
    {hasReading && <FriendlyStep done label={evidenceCount !== undefined ? `Selected ${evidenceCount} relevant piece${evidenceCount === 1 ? '' : 's'} of information` : 'Reading relevant information'} />}
    {hasGeneration && <FriendlyStep done={!generationRunning} active={generationRunning} label={generationRunning ? 'Preparing your answer' : 'Prepared a grounded answer'} />}
    {!running && citationCount !== undefined && <FriendlyStep done label={`${citationCount} source citation${citationCount === 1 ? '' : 's'} prepared`} />}
    {!running && summary && <p className="ml-6 text-[12px] text-faint">{summary.rounds} research pass{summary.rounds === 1 ? '' : 'es'} · {formatElapsed(summary.total_ms)}</p>}
  </div>
}

function FriendlyStep({ label, done = false, active = false }: { label: string; done?: boolean; active?: boolean }) {
  return <div className="flex items-center gap-2 text-[14px] leading-6 text-muted">{active ? <LoaderCircle size={14} className="animate-spin text-brand motion-reduce:animate-none" /> : done ? <Check size={14} className="text-brand" /> : <Circle size={12} className="text-faint" />}<span>{label}</span></div>
}

function runningLabel(events: ResearchTraceEvent[]) {
  if (events.some((event) => event.stage === 'generation' && event.status === 'running')) return 'Preparing your answer…'
  if (events.some((event) => (event.round || 1) > 1)) return 'Looking for a little more information…'
  if (events.some((event) => event.stage === 'page_retrieval' || event.stage === 'evidence')) return 'Reading relevant information…'
  if (events.some((event) => event.stage === 'search')) return 'Searching trusted health sources…'
  return 'Starting trusted research…'
}

function friendlyQuery(query: string) { return query.replace(/^site:\S+\s*/i, '').trim() }
function formatElapsed(ms: number) { return ms >= 1000 ? `${(ms / 1000).toFixed(1)}s` : `${ms}ms` }
