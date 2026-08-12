import { ExternalLink } from 'lucide-react'
import type { SourceReference } from '../../types'

export function SourceReferences({ sources }: { sources: SourceReference[] }) {
  if (!sources.length) return <p className="text-sm text-muted">No source results available.</p>
  return <div className="flex flex-wrap gap-2">
    {sources.map((source) => <a key={`${source.domain}-${source.title}`} href={source.url} target="_blank" rel="noopener noreferrer" className="focus-ring group inline-flex min-w-0 max-w-full items-center gap-2 rounded-xl bg-surface-muted px-3 py-2 transition duration-200 hover:bg-mint-pale">
      <span className="grid h-6 w-6 shrink-0 place-items-center rounded-md bg-mint text-[8px] font-bold text-brand-dark">{initials(source.name)}</span>
      <span className="min-w-0"><span className="block truncate text-[13px] font-semibold leading-5 text-ink">{source.name}</span><span className="block max-w-[220px] truncate text-[12px] leading-4 text-muted">{source.title}</span></span>
      <ExternalLink size={13} className="shrink-0 text-faint group-hover:text-brand" />
    </a>)}
  </div>
}

function initials(name: string) { return name.split(' ').map((part) => part[0]).slice(0, 2).join('') }
