import { ArrowUpRight, CalendarDays, Newspaper } from 'lucide-react'
import { useEffect, useState } from 'react'
import { PageHeader } from '../components/ui/PageHeader'
import { api } from '../services/api'
import type { NewsArticle } from '../types'

const FILTERS = [
  ['all', 'All'], ['research', 'Research'], ['nutrition', 'Nutrition'], ['mental-health', 'Mental Health'], ['public-health', 'Public Health'], ['medicine', 'Medicine'],
] as const

export function NewsPage() {
  const [category, setCategory] = useState('all')
  const [articles, setArticles] = useState<NewsArticle[]>([])
  const [loading, setLoading] = useState(true)
  const [failed, setFailed] = useState(false)

  useEffect(() => {
    setLoading(true)
    setFailed(false)
    api.news(category, 12).then((response) => setArticles(response.articles)).catch(() => {
      setArticles([])
      setFailed(true)
    }).finally(() => setLoading(false))
  }, [category])

  return <div className="mx-auto max-w-[1100px] px-4 py-8 sm:px-6 lg:py-12">
    <div className="flex flex-col justify-between gap-5 md:flex-row md:items-end">
      <PageHeader eyebrow="Health News" title="A calmer way to keep up" description="Recent health and medical stories from reputable publishers, arranged for quick reading." />
      <span className="mb-8 hidden rounded-full bg-lime px-3 py-1.5 text-[11px] font-medium text-lime-dark md:inline-flex">Curated, not personalized</span>
    </div>
    <div className="mb-8 flex gap-2 overflow-x-auto pb-1" aria-label="Filter news by category">{FILTERS.map(([id, label]) => <button key={id} type="button" onClick={() => setCategory(id)} aria-pressed={category === id} className={`focus-ring shrink-0 rounded-full border px-3.5 py-2 text-[12px] font-medium transition ${category === id ? 'border-brand bg-mint text-brand-dark' : 'border-line bg-white text-muted hover:border-mint hover:text-ink'}`}>{label}</button>)}</div>
    {loading ? <NewsSkeleton /> : failed ? <EmptyNews title="Health news couldn’t be loaded" description="Check the API connection and try again." /> : articles.length === 0 ? <EmptyNews title="No stories in this category" description="Try another filter to explore more health news." /> : <div className="divide-y divide-line overflow-hidden rounded-card border border-line bg-white shadow-soft">{articles.map((article, index) => <NewsRow key={article.id} article={article} featured={index === 0} />)}</div>}
  </div>
}

function NewsRow({ article, featured }: { article: NewsArticle; featured: boolean }) {
  return <article className={`group grid gap-4 p-5 transition hover:bg-canvas sm:p-6 ${featured ? 'md:grid-cols-[minmax(0,1fr)_160px]' : 'md:grid-cols-[minmax(0,1fr)_160px]'}`}>
    <div>
      <div className="flex flex-wrap items-center gap-2.5">
        <span className={`rounded-full px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[.08em] ${featured ? 'bg-peach-pale text-peach-dark' : 'bg-mint-pale text-brand-dark'}`}>{article.category.replace('-', ' ')}</span>
        <span className="inline-flex items-center gap-1.5 text-[11px] text-faint"><CalendarDays size={12} />{formatDate(article.published_at)}</span>
      </div>
      <h2 className={`${featured ? 'mt-4 text-[21px] leading-7' : 'mt-3 text-[17px] leading-6'} font-semibold tracking-[-.02em] text-ink transition group-hover:text-brand-dark`}>{article.title}</h2>
      <p className="mt-2 max-w-3xl text-[13px] leading-5 text-muted">{article.summary}</p>
    </div>
    <div className="flex items-end justify-between gap-4 md:flex-col md:items-end md:justify-between">
      <span className="text-[11px] font-medium text-muted">{article.publisher}</span>
      <a href={article.url} target="_blank" rel="noopener noreferrer" className="focus-ring inline-flex items-center gap-1.5 rounded-full px-2 py-1 text-[12px] font-semibold text-brand-dark hover:bg-mint-pale">Read story <ArrowUpRight size={14} /></a>
    </div>
  </article>
}

function NewsSkeleton() {
  return <div aria-label="Loading health news" role="status" className="divide-y divide-line overflow-hidden rounded-card border border-line bg-white">{[1, 2, 3, 4].map((item) => <div key={item} className="animate-pulse p-6"><div className="h-5 w-24 rounded-full bg-mint-pale" /><div className="mt-4 h-5 w-4/5 rounded bg-surface-muted" /><div className="mt-3 h-3 w-full rounded bg-surface-muted" /><div className="mt-2 h-3 w-5/6 rounded bg-surface-muted" /></div>)}</div>
}

function EmptyNews({ title, description }: { title: string; description: string }) {
  return <div className="rounded-card border border-dashed border-line bg-white/70 p-12 text-center"><span className="mx-auto grid h-12 w-12 place-items-center rounded-[16px] bg-peach-pale text-peach-dark"><Newspaper size={21} /></span><h2 className="mt-5 text-[15px] font-semibold text-ink">{title}</h2><p className="mt-2 text-[13px] text-muted">{description}</p></div>
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat(undefined, { month: 'short', day: 'numeric' }).format(new Date(value))
}
