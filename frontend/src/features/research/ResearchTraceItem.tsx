import { AlertTriangle, CheckCircle2, Circle, FileSearch, Link2, ListFilter, LoaderCircle, Search, ShieldCheck, Sparkles } from 'lucide-react'
import type { ResearchStage, ResearchTraceEvent } from '../../types/research'

const STAGE_ICONS: Record<ResearchStage, typeof Search> = { safety: ShieldCheck, search: Search, page_retrieval: FileSearch, evidence: ListFilter, research_decision: Circle, generation: Sparkles, citation: Link2, complete: CheckCircle2 }

export function ResearchTraceItem({ event }: { event: ResearchTraceEvent }) {
  const StageIcon = STAGE_ICONS[event.stage]
  const StatusIcon = event.status === 'running' ? LoaderCircle : event.status === 'warning' || event.status === 'failed' ? AlertTriangle : CheckCircle2
  const technical = [event.tool, event.source_name, event.backend ? displayName(event.backend) : undefined, event.provider ? displayName(event.provider) : undefined, event.model, ...countDetails(event)].filter(Boolean)
  return <li className="relative flex min-w-0 gap-2.5 py-2.5 first:pt-1 last:pb-1">
    <span className="relative mt-0.5 grid h-6 w-6 shrink-0 place-items-center rounded-md bg-white text-muted"><StageIcon size={13} /><StatusIcon size={9} className={`absolute -bottom-1 -right-1 rounded-full bg-white ${event.status === 'running' ? 'animate-spin text-brand motion-reduce:animate-none' : event.status === 'warning' || event.status === 'failed' ? 'text-coral-dark' : 'text-brand'}`} /></span>
    <div className="min-w-0 flex-1"><div className="flex min-w-0 flex-wrap items-center gap-x-2 gap-y-1"><p className="min-w-0 text-[13px] font-semibold leading-5 text-ink">{event.label}</p>{event.round && event.round > 1 && <span className="rounded-full bg-peach-pale px-1.5 py-0.5 text-[11px] font-semibold text-peach-dark">Round {event.round}</span>}<span className="sr-only">{event.status}</span></div>
      {technical.length > 0 && <p className="mt-0.5 break-words text-[12px] leading-5 text-muted">{technical.join(' · ')}</p>}
      {event.query && <p className="mt-1 max-w-full break-words rounded-lg bg-white px-2 py-1.5 font-mono text-[12px] leading-5 text-muted">“{event.query}”</p>}
      {event.message && <p className="mt-1 text-[12px] leading-5 text-muted">{event.message}</p>}
    </div>
  </li>
}

function displayName(value: string) { return value.split(/[-_ ]/).filter(Boolean).map((part) => part[0].toUpperCase() + part.slice(1)).join(' ') }
function countDetails(event: ResearchTraceEvent) {
  const details = []
  if (event.result_count !== undefined) details.push(`${event.result_count} result${event.result_count === 1 ? '' : 's'}`)
  if (event.evidence_count !== undefined) details.push(`${event.evidence_count} evidence item${event.evidence_count === 1 ? '' : 's'}`)
  if (event.citation_count !== undefined) details.push(`${event.citation_count} trusted link${event.citation_count === 1 ? '' : 's'}`)
  if (event.elapsed_ms !== undefined) details.push(event.elapsed_ms >= 1000 ? `${(event.elapsed_ms / 1000).toFixed(1)}s` : `${event.elapsed_ms}ms`)
  return details
}
