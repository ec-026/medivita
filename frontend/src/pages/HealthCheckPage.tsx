import { AlertCircle, CheckCircle2, ClipboardList, LoaderCircle, ShieldAlert, Sparkles } from 'lucide-react'
import { type FormEvent, useState } from 'react'
import { PageHeader } from '../components/ui/PageHeader'
import { SourceReferences } from '../components/ui/SourceReferences'
import { ResearchActivity } from '../features/research/ResearchActivity'
import { mergeTraceEvent } from '../features/research/mergeTrace'
import { api } from '../services/api'
import { useSources } from '../state/SourceContext'
import { useToast } from '../state/ToastContext'
import type { HealthCheckResponse, ResearchTraceEvent } from '../types'

export function HealthCheckPage() {
  const [description, setDescription] = useState('')
  const [result, setResult] = useState<HealthCheckResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [liveTrace, setLiveTrace] = useState<ResearchTraceEvent[]>([])
  const { enabledSourceIds } = useSources()
  const { notify } = useToast()

  const submit = async (event: FormEvent) => {
    event.preventDefault()
    if (description.trim().length < 10 || loading) return
    setLoading(true)
    setResult(null)
    setLiveTrace([])
    try {
      let collectedTrace: ResearchTraceEvent[] = []
      const response = await api.healthCheckWithTrace(description.trim(), enabledSourceIds, (traceEvent) => {
        collectedTrace = mergeTraceEvent(collectedTrace, traceEvent)
        setLiveTrace(collectedTrace)
      })
      if (!response.research_trace && collectedTrace.length > 0) response.research_trace = collectedTrace
      setResult(response)
    } catch (error) {
      notify(error instanceof Error ? error.message : 'The health summary could not be generated.', 'error')
    } finally {
      setLoading(false)
    }
  }

  return <div className="mx-auto max-w-[1120px] px-4 py-8 sm:px-6 lg:py-12">
    <PageHeader eyebrow="Health Check" title="Turn your notes into a clearer summary" description="Describe what you’ve noticed. MediVita will organize it into a calm, non-diagnostic overview grounded in your selected health sources." />
    <div className="grid items-start gap-7 lg:grid-cols-[minmax(0,.88fr)_minmax(0,1.12fr)]">
      <form onSubmit={submit} className="overflow-hidden rounded-card border border-line bg-white shadow-soft">
        <div className="border-b border-peach bg-peach-pale px-5 py-4 sm:px-6">
          <div className="flex items-center gap-3">
            <span className="grid h-9 w-9 place-items-center rounded-xl bg-peach text-coral-dark"><ClipboardList size={18} /></span>
            <div><h2 className="text-[14px] font-semibold text-ink">What have you noticed?</h2><p className="mt-0.5 text-[12px] text-muted">Share patterns and context, not identifying details.</p></div>
          </div>
        </div>
        <div className="p-5 sm:p-6">
          <label htmlFor="health-description" className="text-[12px] font-semibold text-ink">Health notes</label>
          <textarea id="health-description" value={description} onChange={(event) => setDescription(event.target.value)} maxLength={4000} rows={10} placeholder="For example: I’ve had a mild headache most afternoons this week. It seems worse after long screen time and improves after resting…" className="focus-ring mt-2 w-full resize-y rounded-[16px] border border-line bg-canvas px-4 py-3.5 text-[14px] leading-6 text-ink placeholder:text-faint" />
          <div className="mt-2 flex justify-between text-[11px] text-faint"><span>At least 10 characters</span><span>{description.length}/4000</span></div>
          <button disabled={description.trim().length < 10 || loading} className="primary-button mt-5 w-full disabled:cursor-not-allowed disabled:border-line disabled:bg-surface-muted disabled:text-faint">
            {loading ? <><LoaderCircle size={16} className="animate-spin" /> Organizing your notes…</> : <><Sparkles size={16} /> Create health summary</>}
          </button>
          <p className="mt-4 text-center text-[11px] leading-4 text-faint">Informational support only — not a diagnosis or medical assessment.</p>
        </div>
      </form>

      <div>{loading ? <LoadingResult trace={liveTrace} /> : result ? <HealthResult result={result} /> : <EmptyResult />}</div>
    </div>
  </div>
}

function EmptyResult() {
  return <div className="rounded-card border border-dashed border-line bg-white/60 p-10 text-center sm:p-14">
    <span className="mx-auto grid h-12 w-12 place-items-center rounded-[16px] bg-lime text-lime-dark"><Sparkles size={20} /></span>
    <h2 className="mt-5 text-[15px] font-semibold text-ink">A clearer summary will appear here</h2>
    <p className="mx-auto mt-2 max-w-sm text-[13px] leading-5 text-muted">Your notes will be organized into reported symptoms, general considerations, self-care ideas, and signs to seek care.</p>
  </div>
}

function LoadingResult({ trace }: { trace: ResearchTraceEvent[] }) {
  return <div role="status" aria-label="Generating health summary" className="rounded-card border border-line bg-white p-5 shadow-soft sm:p-6">
    <ResearchActivity events={trace} running />
    <div className="mt-7 animate-pulse space-y-7">
      <div><div className="h-3 w-24 rounded bg-mint" /><div className="mt-3 h-3 w-full rounded bg-surface-muted" /><div className="mt-2 h-3 w-5/6 rounded bg-surface-muted" /></div>
      {[1, 2, 3].map((item) => <div key={item}><div className="h-3.5 w-40 rounded bg-peach-pale" /><div className="mt-3 h-3 w-full rounded bg-surface-muted" /><div className="mt-2 h-3 w-4/5 rounded bg-surface-muted" /></div>)}
    </div>
  </div>
}

function HealthResult({ result }: { result: HealthCheckResponse }) {
  const sections = [
    { title: 'What you reported', values: result.reported_symptoms, icon: CheckCircle2, tone: 'bg-mint text-brand-dark' },
    { title: 'General considerations', values: result.general_considerations, icon: AlertCircle, tone: 'bg-lime text-lime-dark' },
    { title: 'Self-care ideas', values: result.self_care, icon: Sparkles, tone: 'bg-peach-pale text-peach-dark' },
    { title: 'When to seek care', values: result.seek_medical_attention, icon: ShieldAlert, tone: 'bg-coral-pale text-coral-dark' },
  ]

  return <article className="rounded-card border border-line bg-white p-5 shadow-soft sm:p-7">
    <div className="flex flex-wrap items-center justify-between gap-3">
      <p className="text-[11px] font-semibold uppercase tracking-[.15em] text-brand-dark">Informational summary</p>
      <span className="rounded-full bg-mint-pale px-2.5 py-1 text-[10px] font-medium text-brand-dark">{result.mode === 'connected' ? 'Researched response' : 'Demo response'}</span>
    </div>
    <h2 className="mt-5 text-[22px] font-semibold tracking-[-.025em] text-ink">Your health notes, organized</h2>
    <p className="mt-2 text-[14px] leading-6 text-muted">{result.summary}</p>
    {result.safety_notice && <div className="mt-5 flex gap-3 rounded-[16px] border border-coral bg-coral-pale p-4 text-[13px] leading-5 text-coral-dark"><ShieldAlert size={17} className="mt-0.5 shrink-0" /><span>{result.safety_notice}</span></div>}
    <ResearchActivity events={result.research_trace} summary={result.research_summary} />
    <div className="mt-7 space-y-7">{sections.map(({ title, values, icon: Icon, tone }) => <section key={title}>
      <h3 className="flex items-center gap-2.5 text-[14px] font-semibold text-ink"><span className={`grid h-7 w-7 place-items-center rounded-lg ${tone}`}><Icon size={14} /></span>{title}</h3>
      <ul className="mt-3 space-y-2.5 pl-9">{values.map((value) => <li key={value} className="relative text-[13px] leading-5 text-muted before:absolute before:-left-4 before:top-[8px] before:h-1 before:w-1 before:rounded-full before:bg-faint">{value}</li>)}</ul>
    </section>)}</div>
    <section className="mt-8 border-t border-line-light pt-5"><h3 className="mb-3 text-[12px] font-semibold text-ink">Sources</h3><SourceReferences sources={result.sources} /></section>
  </article>
}
