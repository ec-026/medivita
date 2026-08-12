import type { ChatResponse, HealthCheckResponse, NewsArticle, ResearchTraceEvent } from '../types'

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000/api'
const parsedTimeout = Number(import.meta.env.VITE_API_TIMEOUT_MS || 45000)
const API_TIMEOUT_MS = Number.isFinite(parsedTimeout) && parsedTimeout > 0 ? parsedTimeout : 45000

export class ApiError extends Error {
  constructor(message: string, public code = 'NETWORK_ERROR') { super(message) }
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const controller = new AbortController()
  const timeout = window.setTimeout(() => controller.abort(), API_TIMEOUT_MS)
  try {
    const response = await fetch(`${API_BASE}${path}`, {
      ...options,
      signal: controller.signal,
      headers: { 'Content-Type': 'application/json', ...options?.headers },
    })
    const body = await response.json().catch(() => ({}))
    if (!response.ok) throw new ApiError(body?.error?.message || 'MediVita could not complete the request.', body?.error?.code)
    return body as T
  } catch (error) {
    if (error instanceof ApiError) throw error
    if (error instanceof DOMException && error.name === 'AbortError') {
      throw new ApiError('The research request took too long. Please try again.', 'REQUEST_TIMEOUT')
    }
    throw new ApiError("We couldn't reach MediVita's service. Please try again.")
  } finally {
    window.clearTimeout(timeout)
  }
}

class StreamUnavailable extends Error {}

interface StreamEnvelope<T> {
  event: 'trace' | 'result' | 'error' | 'done'
  data?: ResearchTraceEvent | T | { code?: string; message?: string }
}

async function streamRequest<T>(
  path: string,
  payload: unknown,
  onTrace: (event: ResearchTraceEvent) => void,
  fallback: () => Promise<T>,
): Promise<T> {
  const controller = new AbortController()
  const timeout = window.setTimeout(() => controller.abort(), API_TIMEOUT_MS)
  let result: T | undefined
  try {
    const response = await fetch(`${API_BASE}${path}`, {
      method: 'POST',
      signal: controller.signal,
      headers: { 'Content-Type': 'application/json', Accept: 'application/x-ndjson' },
      body: JSON.stringify(payload),
    })
    if (!response.ok) {
      if (response.status === 404 || response.status === 405) throw new StreamUnavailable()
      const body = await response.json().catch(() => ({}))
      throw new ApiError(body?.error?.message || 'MediVita could not complete the request.', body?.error?.code)
    }
    if (!response.body) throw new StreamUnavailable()

    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''
    while (true) {
      const { done, value } = await reader.read()
      buffer += decoder.decode(value, { stream: !done })
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''
      for (const line of lines) {
        if (!line.trim()) continue
        const envelope = JSON.parse(line) as StreamEnvelope<T>
        if (envelope.event === 'trace' && envelope.data) {
          onTrace(envelope.data as ResearchTraceEvent)
        } else if (envelope.event === 'result' && envelope.data) {
          result = envelope.data as T
        } else if (envelope.event === 'error') {
          const error = envelope.data as { code?: string; message?: string } | undefined
          throw new ApiError(
            error?.message || 'MediVita could not complete the request.',
            error?.code || 'STREAM_ERROR',
          )
        }
      }
      if (done) break
    }
    if (result) return result
    throw new StreamUnavailable()
  } catch (error) {
    if (result) return result
    if (error instanceof ApiError) throw error
    return fallback()
  } finally {
    window.clearTimeout(timeout)
  }
}

export const api = {
  chat: (message: string, enabledSources: string[], history: { role: string; content: string }[]) =>
    request<ChatResponse>('/chat', { method: 'POST', body: JSON.stringify({ message, enabled_sources: enabledSources, history }) }),
  healthCheck: (description: string, enabledSources: string[]) =>
    request<HealthCheckResponse>('/health-check', { method: 'POST', body: JSON.stringify({ description, enabled_sources: enabledSources }) }),
  chatWithTrace: (
    message: string,
    enabledSources: string[],
    history: { role: string; content: string }[],
    onTrace: (event: ResearchTraceEvent) => void,
  ) => streamRequest<ChatResponse>(
    '/chat/stream',
    { message, enabled_sources: enabledSources, history },
    onTrace,
    () => api.chat(message, enabledSources, history),
  ),
  healthCheckWithTrace: (
    description: string,
    enabledSources: string[],
    onTrace: (event: ResearchTraceEvent) => void,
  ) => streamRequest<HealthCheckResponse>(
    '/health-check/stream',
    { description, enabled_sources: enabledSources },
    onTrace,
    () => api.healthCheck(description, enabledSources),
  ),
  news: (category = 'all', limit = 12) => request<{ articles: NewsArticle[]; mode: string }>(`/news?category=${encodeURIComponent(category)}&limit=${limit}`),
}
