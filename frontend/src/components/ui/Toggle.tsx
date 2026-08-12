interface ToggleProps { checked: boolean; onChange: () => void; label: string }
export function Toggle({ checked, onChange, label }: ToggleProps) {
  return (
    <button type="button" role="switch" aria-checked={checked} aria-label={label} onClick={onChange}
      data-state={checked ? 'on' : 'off'}
      className={`focus-ring relative h-6 w-11 shrink-0 overflow-hidden rounded-full border transition-colors duration-200 ${checked ? 'border-brand/50 bg-mint' : 'border-line bg-surface-muted'}`}>
      <span aria-hidden="true" className={`absolute left-[3px] top-[3px] h-4 w-4 rounded-full shadow-sm transition-[transform,background-color] duration-200 ${checked ? 'translate-x-5 bg-brand' : 'translate-x-0 bg-faint'}`} />
    </button>
  )
}
