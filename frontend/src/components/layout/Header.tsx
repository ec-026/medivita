import { Menu, SlidersHorizontal } from 'lucide-react'
import { BrandMark } from '../ui/BrandMark'

export function Header({ onMenu, onContext }: { onMenu: () => void; onContext: () => void }) {
  return <header className="fixed inset-x-0 top-0 z-50 flex h-14 items-center border-b border-line/80 bg-canvas/95 px-4 backdrop-blur-xl xl:hidden">
    <button type="button" aria-label="Open navigation" onClick={onMenu} className="ghost-button mr-2 h-9 w-9 md:hidden"><Menu size={19} /></button>
    <div className="flex min-w-0 items-center gap-3">
      <BrandMark className="h-8 w-8 shrink-0" />
      <div className="min-w-0"><p className="text-[16px] font-semibold leading-5 tracking-[-.02em] text-ink">MediVita</p><p className="hidden truncate text-[10px] text-muted sm:block">Health information, thoughtfully researched</p></div>
    </div>
    <div className="ml-auto flex items-center gap-2 sm:gap-3">
      <span className="hidden rounded-full bg-lime-pale px-3 py-1.5 text-[11px] font-medium text-lime-dark sm:inline-flex">Informational use only</span>
      <button type="button" aria-label="Open trusted sources panel" onClick={onContext} className="ghost-button h-9 gap-2 px-2.5"><SlidersHorizontal size={17} /><span className="hidden text-xs font-semibold sm:inline">Sources</span></button>
    </div>
  </header>
}
