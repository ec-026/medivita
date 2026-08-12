export function BrandMark({ className = 'h-9 w-9' }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 40 40" fill="none" aria-hidden="true">
      <rect width="40" height="40" rx="11" fill="#2F6F58" />
      <path d="M10 23h5l2.4-6 4.2 11 2.8-7H30" stroke="white" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M20 7.5c5.8 0 10.5 2 10.5 2v8.2c0 7.4-4.8 12-10.5 14.8-5.7-2.8-10.5-7.4-10.5-14.8V9.5s4.7-2 10.5-2Z" stroke="white" strokeWidth="1.5" opacity=".5" />
    </svg>
  )
}
