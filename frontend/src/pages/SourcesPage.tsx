import { Check, Info, ShieldCheck } from 'lucide-react'
import { PageHeader } from '../components/ui/PageHeader'
import { Toggle } from '../components/ui/Toggle'
import { TRUSTED_SOURCES } from '../data/sources'
import { useSources } from '../state/SourceContext'

export function SourcesPage() {
  const { isEnabled, toggleSource, enabledSourceIds } = useSources()

  return <div className="mx-auto max-w-[980px] px-4 py-8 sm:px-6 lg:py-12">
    <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
      <PageHeader eyebrow="Source Settings" title="Choose where research starts" description="MediVita searches only the trusted health organizations you enable here. You can change this at any time." />
      <div className="mb-8 shrink-0 rounded-full bg-mint px-3 py-1.5 text-[11px] font-semibold text-brand-dark">{enabledSourceIds.length} of {TRUSTED_SOURCES.length} enabled</div>
    </div>

    <div className="mb-6 flex gap-3 rounded-[16px] border border-lime bg-lime-pale p-4 text-[13px] leading-5 text-lime-dark"><Info size={17} className="mt-0.5 shrink-0" /><p>Enabled sources may be consulted during research, but not every response needs every source. No listed organization endorses MediVita.</p></div>

    <div className="divide-y divide-line overflow-hidden rounded-card border border-line bg-white shadow-soft">{TRUSTED_SOURCES.map((source) => {
      const enabled = isEnabled(source.id)
      return <article key={source.id} className="flex flex-col gap-4 p-5 transition hover:bg-canvas sm:flex-row sm:items-center sm:p-6">
        <span className={`grid h-11 w-11 shrink-0 place-items-center rounded-[14px] text-[11px] font-bold ${enabled ? 'bg-mint text-brand-dark' : 'bg-surface-muted text-muted'}`}>{source.name.split(' ').map((part) => part[0]).slice(0, 2).join('')}</span>
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2"><h2 className="text-[14px] font-semibold text-ink">{source.name}</h2>{enabled && <span className="inline-flex items-center gap-1 rounded-full bg-mint-pale px-2 py-0.5 text-[10px] font-medium text-brand-dark"><Check size={11} /> Enabled</span>}</div>
          <p className="mt-0.5 text-[11px] text-faint">{source.domain}</p>
          <p className="mt-2 text-[13px] leading-5 text-muted">{source.description}</p>
        </div>
        <div className="flex items-center justify-between gap-4 sm:justify-end">
          <ShieldCheck size={17} className={enabled ? 'text-brand' : 'text-faint'} aria-hidden="true" />
          <Toggle checked={enabled} onChange={() => toggleSource(source.id)} label={`${enabled ? 'Disable' : 'Enable'} ${source.name}`} />
        </div>
      </article>
    })}</div>
    <p className="mt-4 text-[11px] leading-5 text-faint">Preferences are stored only in this browser. Disabling a source changes future research, not existing responses.</p>
  </div>
}
