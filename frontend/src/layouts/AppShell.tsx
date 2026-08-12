import { useEffect, useState } from 'react'
import { Outlet, useLocation } from 'react-router-dom'
import { Header } from '../components/layout/Header'
import { RightPanel } from '../components/layout/RightPanel'
import { Sidebar } from '../components/layout/Sidebar'

const LEFT_KEY = 'medivita:left-sidebar-collapsed'
const RIGHT_KEY = 'medivita:right-sidebar-collapsed'

function storedBoolean(key: string) {
  try { return localStorage.getItem(key) === 'true' } catch { return false }
}

export function AppShell() {
  const [navigationOpen, setNavigationOpen] = useState(false)
  const [contextOpen, setContextOpen] = useState(false)
  const [leftCollapsed, setLeftCollapsed] = useState(() => storedBoolean(LEFT_KEY))
  const [rightCollapsed, setRightCollapsed] = useState(() => storedBoolean(RIGHT_KEY))
  const location = useLocation()
  useEffect(() => { setNavigationOpen(false); setContextOpen(false) }, [location.pathname])
  const toggleLeft = () => setLeftCollapsed((value) => { localStorage.setItem(LEFT_KEY, String(!value)); return !value })
  const toggleRight = () => setRightCollapsed((value) => { localStorage.setItem(RIGHT_KEY, String(!value)); return !value })

  return <div className="min-h-screen bg-canvas text-ink">
    <Header onMenu={() => setNavigationOpen(true)} onContext={() => setContextOpen(true)} />
    <aside className={`fixed bottom-0 left-0 z-40 hidden border-r border-line/60 bg-surface transition-[width] duration-200 md:block md:top-14 xl:top-0 ${leftCollapsed ? 'w-[72px]' : 'w-[236px]'}`}><Sidebar collapsed={leftCollapsed} onToggle={toggleLeft} /></aside>
    <main className={`min-h-screen pt-14 transition-[padding] duration-200 xl:pt-0 ${leftCollapsed ? 'md:pl-[72px]' : 'md:pl-[236px]'} ${rightCollapsed ? 'xl:pr-[56px]' : 'xl:pr-[300px]'}`}><Outlet /></main>
    <aside className={`fixed bottom-0 right-0 top-0 z-40 hidden border-l border-line/60 bg-surface transition-[width] duration-200 xl:block ${rightCollapsed ? 'w-[56px]' : 'w-[300px]'}`}><RightPanel collapsed={rightCollapsed} onToggle={toggleRight} /></aside>

    {navigationOpen && <Drawer side="left" label="Navigation" onClose={() => setNavigationOpen(false)}><Sidebar mobile onNavigate={() => setNavigationOpen(false)} /></Drawer>}
    {contextOpen && <Drawer side="right" label="Trusted sources" onClose={() => setContextOpen(false)}><RightPanel mobile onNavigate={() => setContextOpen(false)} /></Drawer>}
  </div>
}

function Drawer({ side, label, onClose, children }: { side: 'left' | 'right'; label: string; onClose: () => void; children: React.ReactNode }) {
  return <div className="fixed inset-0 z-[70] xl:hidden">
    <button aria-label={`Close ${label.toLowerCase()}`} className="absolute inset-0 bg-stone-950/25 backdrop-blur-[2px]" onClick={onClose} />
    <aside role="dialog" aria-modal="true" aria-label={label} className={`absolute inset-y-0 ${side === 'left' ? 'left-0' : 'right-0'} w-[min(320px,88vw)] bg-white shadow-float`}>{children}</aside>
  </div>
}
