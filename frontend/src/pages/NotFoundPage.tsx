import { ArrowLeft } from 'lucide-react'
import { Link } from 'react-router-dom'
import { BrandMark } from '../components/ui/BrandMark'

export function NotFoundPage() {
  return <div className="grid min-h-screen place-items-center px-4">
    <div className="max-w-md text-center">
      <span className="mx-auto grid h-14 w-14 place-items-center rounded-[20px] bg-mint shadow-soft"><BrandMark className="h-8 w-8" /></span>
      <p className="mt-7 text-[11px] font-semibold uppercase tracking-[.18em] text-brand-dark">Error 404</p>
      <h1 className="mt-3 text-[32px] font-semibold tracking-[-.04em] text-ink">This page wandered off</h1>
      <p className="mt-3 text-[14px] leading-6 text-muted">The page you’re looking for isn’t part of the MediVita workspace.</p>
      <Link to="/chat" className="primary-button mt-7"><ArrowLeft size={16} /> Return to MediVita</Link>
    </div>
  </div>
}
