import { ArrowRight, Newspaper, PanelRightClose, PanelRightOpen, ShieldCheck } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { TRUSTED_SOURCES } from '../../data/sources'
import { api } from '../../services/api'
import { useSources } from '../../state/SourceContext'
import type { NewsArticle } from '../../types'
import { Toggle } from '../ui/Toggle'

export function RightPanel({
  collapsed = false,
  onToggle,
  mobile = false,
  onNavigate,
}: {
  collapsed?: boolean
  onToggle?: () => void
  mobile?: boolean
  onNavigate?: () => void
}) {
  const { isEnabled, toggleSource, enabledSourceIds } = useSources()
  const [news, setNews] = useState<NewsArticle[]>([])
  const [newsLoading, setNewsLoading] = useState(true)
  const compact = collapsed && !mobile
  useEffect(() => { api.news('all', 3).then((response) => setNews(response.articles)).catch(() => setNews([])).finally(() => setNewsLoading(false)) }, [])

  if (compact) return <div className="flex h-full flex-col items-center bg-surface px-2 py-4">
    <button type="button" onClick={onToggle} aria-label="Expand context sidebar" title="Expand context sidebar" className="ghost-button h-11 w-11"><PanelRightOpen size={18} /></button>
    <Link to="/sources" aria-label={`${enabledSourceIds.length} trusted sources enabled`} title="Trusted sources" className="ghost-button mt-5 h-11 w-11"><ShieldCheck size={18} /></Link>
    <Link to="/news" aria-label="Health news" title="Health news" className="ghost-button mt-1 h-11 w-11"><Newspaper size={18} /></Link>
  </div>

  return <div className="h-full overflow-y-auto bg-surface px-5 py-5">
    <div className="flex min-h-10 items-start justify-between gap-3">
      <div className="pt-0.5"><h2 className="text-[15px] font-semibold leading-5 text-ink">Trusted sources</h2><p className="mt-0.5 text-[13px] leading-4 text-muted">{enabledSourceIds.length} enabled for research</p></div>
      {!mobile && <button type="button" onClick={onToggle} aria-label="Collapse context sidebar" title="Collapse context sidebar" className="ghost-button h-10 w-10 shrink-0"><PanelRightClose size={17} /></button>}
    </div>
    <div className="mt-3 space-y-1">
      {TRUSTED_SOURCES.map((source) => <div key={source.id} className="grid min-h-[54px] grid-cols-[32px_minmax(0,1fr)_44px] items-center gap-3 rounded-xl px-2 py-2 transition-colors hover:bg-surface-muted">
        <span className={`grid h-8 w-8 place-items-center rounded-lg text-[9px] font-bold ${isEnabled(source.id) ? 'bg-mint text-brand-dark' : 'bg-stone-100 text-faint'}`}>{initials(source.name)}</span>
        <span className="min-w-0"><span className="block truncate text-[15px] font-medium leading-5 text-ink">{source.name}</span><span className="block truncate text-[13px] leading-4 text-faint">{source.domain}</span></span>
        <Toggle checked={isEnabled(source.id)} onChange={() => toggleSource(source.id)} label={`${isEnabled(source.id) ? 'Disable' : 'Enable'} ${source.name}`} />
      </div>)}
    </div>
    <Link to="/sources" onClick={onNavigate} className="focus-ring mt-3 inline-flex min-h-9 items-center gap-1 rounded-lg px-1 text-[13px] font-semibold text-brand hover:bg-mint-pale hover:text-brand-dark">Manage sources <ArrowRight size={13} /></Link>

    <div className="my-6 border-t border-line/70" />
    <section>
      <div className="flex min-h-8 items-center justify-between"><h2 className="text-[15px] font-semibold leading-5 text-ink">Latest in health</h2><Newspaper size={16} className="text-coral-dark" /></div>
      <div className="mt-3 space-y-5">
        {news.length ? news.map((article) => <a key={article.id} href={article.url} target="_blank" rel="noopener noreferrer" className="group block">
          <span className="text-[11px] font-semibold uppercase tracking-[.09em] text-coral-dark">{article.category.replace('-', ' ')}</span>
          <h3 className="mt-1.5 text-[14px] font-medium leading-[1.55] text-ink group-hover:text-brand">{article.title}</h3>
          <p className="mt-1.5 text-[12px] leading-4 text-faint">{article.publisher} · {formatDate(article.published_at)}</p>
        </a>) : newsLoading ? [1, 2, 3].map((item) => <div key={item} className="animate-pulse motion-reduce:animate-none"><div className="h-2 w-16 rounded bg-peach-pale" /><div className="mt-2 h-3 w-full rounded bg-stone-100" /><div className="mt-1 h-3 w-3/4 rounded bg-stone-100" /></div>) : <p className="rounded-xl bg-peach-pale px-3 py-3 text-[13px] leading-5 text-peach-dark">Health news is unavailable right now. The rest of MediVita still works normally.</p>}
      </div>
      <Link to="/news" onClick={onNavigate} className="focus-ring mt-4 inline-flex min-h-9 items-center gap-1 rounded-lg text-[13px] font-semibold text-brand hover:text-brand-dark">View all news <ArrowRight size={13} /></Link>
    </section>
  </div>
}

function initials(name: string) { return name.split(' ').map((part) => part[0]).slice(0, 2).join('') }
function formatDate(value: string) { return new Intl.DateTimeFormat(undefined, { month: 'short', day: 'numeric' }).format(new Date(value)) }
