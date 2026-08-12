import { X } from 'lucide-react'
import { useToast } from '../../state/ToastContext'

export function ToastViewport() {
  const { toasts, dismiss } = useToast()
  return <div className="fixed bottom-5 right-5 z-[80] flex w-[min(360px,calc(100vw-40px))] flex-col gap-2" aria-live="polite">
    {toasts.map((toast) => <div key={toast.id} className={`flex items-center gap-3 rounded-[16px] border bg-white px-4 py-3 text-[13px] shadow-float ${toast.tone === 'error' ? 'border-coral bg-coral-pale text-coral-dark' : 'border-mint bg-mint-pale text-ink'}`}>
      <span className="flex-1 leading-5">{toast.message}</span><button aria-label="Dismiss notification" onClick={() => dismiss(toast.id)} className="focus-ring rounded-full p-1 text-muted hover:bg-white/70"><X size={15} /></button>
    </div>)}
  </div>
}
