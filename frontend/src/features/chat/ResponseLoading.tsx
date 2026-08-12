import { BrandMark } from '../../components/ui/BrandMark'
import type { ResearchTraceEvent } from '../../types'
import { ResearchActivity } from '../research/ResearchActivity'

export function ResponseLoading({ trace }: { trace?: ResearchTraceEvent[] }) {
  return <div className="pb-9" aria-label="MediVita is researching a response" role="status">
    <div className="mb-3 flex items-center gap-2.5"><BrandMark className="h-7 w-7" /><div><p className="text-[13px] font-semibold text-ink">MediVita</p><p className="text-[10px] text-faint">Working on your question</p></div></div>
    {trace?.length ? <ResearchActivity events={trace} running /> : <div className="flex items-center gap-2 py-2 text-[12px] text-muted"><span className="h-2 w-2 animate-pulse rounded-full bg-mint-dark motion-reduce:animate-none" />Understanding your question…</div>}
  </div>
}
