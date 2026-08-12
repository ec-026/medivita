import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from 'react'

interface Toast { id: number; message: string; tone: 'default' | 'error' }
interface ToastContextValue { toasts: Toast[]; notify: (message: string, tone?: Toast['tone']) => void; dismiss: (id: number) => void }

const ToastContext = createContext<ToastContextValue | null>(null)

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([])
  const dismiss = useCallback((id: number) => setToasts((items) => items.filter((item) => item.id !== id)), [])
  const notify = useCallback((message: string, tone: Toast['tone'] = 'default') => {
    const id = Date.now()
    setToasts((items) => [...items.slice(-2), { id, message, tone }])
    window.setTimeout(() => dismiss(id), 4000)
  }, [dismiss])
  const value = useMemo(() => ({ toasts, notify, dismiss }), [dismiss, notify, toasts])
  return <ToastContext.Provider value={value}>{children}</ToastContext.Provider>
}

export function useToast() {
  const context = useContext(ToastContext)
  if (!context) throw new Error('useToast must be used within ToastProvider')
  return context
}
