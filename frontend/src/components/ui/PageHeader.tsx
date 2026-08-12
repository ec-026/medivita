export function PageHeader({ eyebrow, title, description }: { eyebrow?: string; title: string; description: string }) {
  return <header className="mb-8 max-w-2xl">
    {eyebrow && <p className="mb-2 text-[11px] font-semibold uppercase tracking-[.16em] text-brand-dark">{eyebrow}</p>}
    <h1 className="text-[28px] font-semibold tracking-[-.035em] text-ink sm:text-[32px]">{title}</h1>
    <p className="mt-2 text-[14px] leading-6 text-muted">{description}</p>
  </header>
}
