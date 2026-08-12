import '@fontsource/inter/latin-400.css'
import '@fontsource/inter/latin-500.css'
import '@fontsource/inter/latin-600.css'
import '@fontsource/inter/latin-700.css'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import App from './App'
import { ToastViewport } from './components/ui/ToastViewport'
import { ConversationProvider } from './state/ConversationContext'
import { SourceProvider } from './state/SourceContext'
import { ToastProvider } from './state/ToastContext'
import './styles.css'

createRoot(document.getElementById('root')!).render(
  <StrictMode><BrowserRouter><ToastProvider><SourceProvider><ConversationProvider><App /><ToastViewport /></ConversationProvider></SourceProvider></ToastProvider></BrowserRouter></StrictMode>,
)
