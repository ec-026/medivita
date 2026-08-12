import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { expect, test, vi } from 'vitest'
import App from '../src/App'
import { ToastViewport } from '../src/components/ui/ToastViewport'
import { ConversationProvider } from '../src/state/ConversationContext'
import { SourceProvider } from '../src/state/SourceContext'
import { ToastProvider } from '../src/state/ToastContext'

const sources = [
  { name: 'Mayo Clinic', domain: 'mayoclinic.org', title: 'General health information - source homepage', url: 'https://mayoclinic.org/' },
]

function jsonResponse(body: unknown, ok = true) {
  return Promise.resolve({ ok, json: () => Promise.resolve(body) } as Response)
}

function ndjsonResponse(events: unknown[]) {
  const encoded = new TextEncoder().encode(events.map((event) => JSON.stringify(event)).join('\n') + '\n')
  let delivered = false
  return Promise.resolve({
    ok: true,
    status: 200,
    body: {
      getReader: () => ({
        read: () => {
          if (delivered) return Promise.resolve({ done: true, value: undefined })
          delivered = true
          return Promise.resolve({ done: false, value: encoded })
        },
      }),
    },
  } as unknown as Response)
}

function mockApi() {
  return vi.spyOn(globalThis, 'fetch').mockImplementation((input) => {
    const url = String(input)
    if (url.includes('/news')) return jsonResponse({ articles: [{ id: '1', title: 'Movement and brain health', summary: 'A research summary.', category: 'research', publisher: 'MediVita Research Desk', published_at: new Date().toISOString(), url: 'https://www.who.int/news-room' }], mode: 'demo' })
    if (url.includes('/chat')) return jsonResponse({ answer: 'Headaches have many possible triggers.', sections: [{ title: 'Overview', content: 'Headaches have many possible triggers.' }], sources, safety_notice: null, mode: 'demo', disclaimer: 'General health information only.' })
    if (url.includes('/health-check')) return jsonResponse({ summary: 'This summary organizes the reported details.', reported_symptoms: ['headache'], general_considerations: ['Patterns matter.'], self_care: ['Record changes.'], seek_medical_attention: ['Seek advice if symptoms worsen.'], sources, safety_notice: null, mode: 'demo' })
    return jsonResponse({}, false)
  })
}

function renderApp(route = '/chat') {
  return render(<MemoryRouter initialEntries={[route]}><ToastProvider><SourceProvider><ConversationProvider><App /><ToastViewport /></ConversationProvider></SourceProvider></ToastProvider></MemoryRouter>)
}

test('primary navigation opens Health Check', async () => {
  mockApi(); renderApp()
  await userEvent.click(screen.getByRole('link', { name: 'Health Check' }))
  expect(screen.getByRole('heading', { name: 'Turn your notes into a clearer summary' })).toBeInTheDocument()
})

test('desktop sidebars collapse independently and persist across remounts', async () => {
  mockApi()
  const firstRender = renderApp()
  await userEvent.click(screen.getByRole('button', { name: 'Collapse navigation sidebar' }))
  expect(localStorage.getItem('medivita:left-sidebar-collapsed')).toBe('true')
  expect(screen.getByRole('button', { name: 'Expand navigation sidebar' })).toBeInTheDocument()
  expect(screen.getByRole('link', { name: 'Chat' })).toHaveAttribute('title', 'Chat')
  expect(screen.getByRole('button', { name: 'Collapse context sidebar' })).toBeInTheDocument()

  await userEvent.click(screen.getByRole('button', { name: 'Collapse context sidebar' }))
  expect(localStorage.getItem('medivita:right-sidebar-collapsed')).toBe('true')
  expect(screen.getByRole('button', { name: 'Expand context sidebar' })).toBeInTheDocument()
  firstRender.unmount()

  renderApp()
  expect(screen.getByRole('button', { name: 'Expand navigation sidebar' })).toBeInTheDocument()
  expect(screen.getByRole('button', { name: 'Expand context sidebar' })).toBeInTheDocument()
})

test('conversation history scrolls independently from the privacy footer', () => {
  mockApi(); renderApp()
  const conversationScroll = screen.getByTestId('conversation-scroll')
  const privacyFooter = screen.getByTestId('privacy-footer')
  expect(conversationScroll).toHaveClass('overflow-y-auto')
  expect(conversationScroll).not.toContainElement(privacyFooter)
  expect(screen.getByTestId('conversation-region')).toContainElement(conversationScroll)
})

test('mobile header opens separate navigation and source drawers', async () => {
  mockApi(); renderApp()
  await userEvent.click(screen.getByRole('button', { name: 'Open navigation' }))
  const navigation = screen.getByRole('dialog', { name: 'Navigation' })
  expect(within(navigation).getByRole('link', { name: 'Health Check' })).toBeInTheDocument()
  await userEvent.click(screen.getByRole('button', { name: 'Close navigation' }))

  await userEvent.click(screen.getByRole('button', { name: 'Open trusted sources panel' }))
  const sourcesDrawer = screen.getByRole('dialog', { name: 'Trusted sources' })
  expect(within(sourcesDrawer).getByRole('switch', { name: 'Disable Mayo Clinic' })).toBeInTheDocument()
})

test('source toggles persist and never allow zero sources', async () => {
  mockApi(); renderApp('/sources')
  const page = within(screen.getByRole('main'))
  await userEvent.click(page.getByRole('switch', { name: 'Disable Healthline' }))
  expect(localStorage.getItem('medivita:trusted-sources')).not.toContain('healthline')
  await userEvent.click(page.getByRole('switch', { name: 'Disable Cleveland Clinic' }))
  await userEvent.click(page.getByRole('switch', { name: 'Disable Mayo Clinic' }))
  await userEvent.click(page.getByRole('switch', { name: 'Disable WebMD' }))
  expect(await screen.findByText('Keep at least one trusted source enabled.')).toBeInTheDocument()
  expect(page.getByRole('switch', { name: 'Disable WebMD' })).toHaveAttribute('aria-checked', 'true')
})

test('a suggested prompt starts chat and renders the response', async () => {
  const fetchMock = mockApi(); renderApp()
  await userEvent.click(screen.getByRole('button', { name: /Common migraine triggers/i }))
  expect(await screen.findByText('Headaches have many possible triggers.')).toBeInTheDocument()
  expect(screen.getAllByText('Sources').length).toBeGreaterThan(0)
  const chatCall = fetchMock.mock.calls.find(([url]) => String(url).includes('/chat'))
  const requestBody = JSON.parse(String((chatCall?.[1] as RequestInit).body))
  expect(requestBody.enabled_sources).toEqual(['healthline', 'cleveland-clinic', 'mayo-clinic', 'webmd'])
})

test('connected chat renders only the retrieved citation URL', async () => {
  vi.spyOn(globalThis, 'fetch').mockImplementation((input) => {
    if (String(input).includes('/chat')) return jsonResponse({
      answer: 'Grounded overview.',
      sections: [{ title: 'Overview', content: 'Grounded overview.' }],
      sources: [{ name: 'Mayo Clinic', domain: 'mayoclinic.org', title: 'Sleep article', url: 'https://www.mayoclinic.org/healthy-lifestyle/adult-health/in-depth/sleep/art-00001' }],
      safety_notice: null,
      mode: 'connected',
      disclaimer: 'General health information only.',
    })
    return jsonResponse({}, false)
  })
  renderApp()
  await userEvent.click(screen.getByRole('button', { name: /Common migraine triggers/i }))
  expect(await screen.findByText('Researched response')).toBeInTheDocument()
  expect(screen.getByRole('link', { name: /Mayo Clinic/ })).toHaveAttribute('href', 'https://www.mayoclinic.org/healthy-lifestyle/adult-health/in-depth/sleep/art-00001')
})

test('streamed research trace is layered and persists with the conversation', async () => {
  const trace = [
    { id: 'safety-1', stage: 'safety', status: 'completed', label: 'Safety screening complete', tool: 'Deterministic safety rules' },
    { id: 'search-1', stage: 'search', status: 'completed', label: 'Mayo Clinic search complete', tool: 'DDGS Search', source_id: 'mayo-clinic', source_name: 'Mayo Clinic', backend: 'bing', query: 'site:mayoclinic.org migraine symptoms', result_count: 2, round: 1 },
    { id: 'generation-1', stage: 'generation', status: 'completed', label: 'Grounded generation complete', provider: 'groq', model: 'openai/gpt-oss-20b', round: 1 },
  ]
  const response = {
    answer: 'Grounded overview.', sections: [{ title: 'Overview', content: 'Grounded overview.' }], sources, safety_notice: null, mode: 'connected', disclaimer: 'General health information only.', research_trace: trace, research_summary: { rounds: 1, evidence_count: 2, citation_count: 1, total_ms: 1200 },
  }
  vi.spyOn(globalThis, 'fetch').mockImplementation((input) => {
    if (String(input).includes('/chat/stream')) return ndjsonResponse([...trace.map((data) => ({ event: 'trace', data })), { event: 'result', data: response }, { event: 'done' }])
    return jsonResponse({}, false)
  })
  const firstRender = renderApp()
  await userEvent.click(screen.getByRole('button', { name: /Common migraine triggers/i }))
  await userEvent.click(await screen.findByRole('button', { name: /Research complete/ }))
  expect(screen.getByText(/Searched:.*migraine symptoms/)).toBeInTheDocument()
  expect(screen.queryByText(/site:mayoclinic\.org/)).not.toBeInTheDocument()
  await userEvent.click(screen.getByRole('button', { name: /Details/ }))
  expect(screen.getByText(/site:mayoclinic\.org migraine symptoms/)).toBeInTheDocument()
  expect(screen.getByText(/DDGS Search.*Mayo Clinic.*Bing.*2 results/)).toBeInTheDocument()
  expect(screen.getByText(/Groq.*openai\/gpt-oss-20b/)).toBeInTheDocument()
  expect(localStorage.getItem('medivita:conversations')).toContain('research_trace')

  firstRender.unmount()
  renderApp()
  await userEvent.click(await screen.findByRole('button', { name: /Research complete/ }))
  await userEvent.click(screen.getByRole('button', { name: /Details/ }))
  expect(screen.getByText(/site:mayoclinic\.org migraine symptoms/)).toBeInTheDocument()
})

test('stream transport failure falls back once to the standard chat endpoint', async () => {
  const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation((input) => {
    if (String(input).includes('/chat/stream')) return Promise.reject(new TypeError('stream unavailable'))
    if (String(input).endsWith('/chat')) return jsonResponse({ answer: 'Fallback overview.', sections: [{ title: 'Overview', content: 'Fallback overview.' }], sources, safety_notice: null, mode: 'demo', disclaimer: 'General health information only.' })
    return jsonResponse({}, false)
  })
  renderApp()
  await userEvent.click(screen.getByRole('button', { name: /Common migraine triggers/i }))
  expect(await screen.findByText('Fallback overview.')).toBeInTheDocument()
  expect(fetchMock.mock.calls.filter(([url]) => String(url).includes('/chat')).length).toBe(2)
  expect(screen.queryByText(/DDGS Search|Groq/)).not.toBeInTheDocument()
})

test('Health Check reuses streamed research activity without changing its result contract', async () => {
  const trace = [{ id: 'evidence-1', stage: 'evidence', status: 'completed', label: 'Relevant evidence selected', tool: 'MediVita Evidence Ranker', evidence_count: 1, round: 1 }]
  vi.spyOn(globalThis, 'fetch').mockImplementation((input) => {
    if (String(input).includes('/health-check/stream')) return ndjsonResponse([
      { event: 'trace', data: trace[0] },
      { event: 'result', data: { summary: 'This summary organizes the reported details.', reported_symptoms: ['headache'], general_considerations: ['Patterns matter.'], self_care: ['Record changes.'], seek_medical_attention: ['Seek advice if symptoms worsen.'], sources, safety_notice: null, mode: 'connected', research_trace: trace, research_summary: { rounds: 1, evidence_count: 1, citation_count: 1, total_ms: 700 } } },
      { event: 'done' },
    ])
    return jsonResponse({}, false)
  })
  renderApp('/health-check')
  await userEvent.type(screen.getByLabelText('Health notes'), 'I have had a headache for two days.')
  await userEvent.click(screen.getByRole('button', { name: 'Create health summary' }))
  expect(await screen.findByText('This summary organizes the reported details.')).toBeInTheDocument()
  await userEvent.click(screen.getByRole('button', { name: /Research complete/ }))
  await userEvent.click(screen.getByRole('button', { name: /Details/ }))
  expect(screen.getByText(/MediVita Evidence Ranker.*1 evidence item/)).toBeInTheDocument()
  expect(screen.getByText('What you reported')).toBeInTheDocument()
})

test('rate-limit errors surface the backend message', async () => {
  vi.spyOn(globalThis, 'fetch').mockImplementation((input) => {
    if (String(input).includes('/chat')) return jsonResponse({ error: { code: 'AI_RATE_LIMITED', message: 'The AI provider is temporarily rate limited. Please try again shortly.' } }, false)
    return jsonResponse({}, false)
  })
  renderApp()
  await userEvent.click(screen.getByRole('button', { name: /Common migraine triggers/i }))
  expect(await screen.findByText('The AI provider is temporarily rate limited. Please try again shortly.')).toBeInTheDocument()
})

test('Health Check submits a description and renders structured output', async () => {
  mockApi(); renderApp('/health-check')
  await userEvent.type(screen.getByLabelText('Health notes'), 'I have had a headache for two days.')
  await userEvent.click(screen.getByRole('button', { name: 'Create health summary' }))
  expect(await screen.findByText('This summary organizes the reported details.')).toBeInTheDocument()
  expect(screen.getByText('What you reported')).toBeInTheDocument()
})

test('news filtering requests the selected category', async () => {
  const fetchMock = mockApi(); renderApp('/news')
  expect(await screen.findByText('Movement and brain health')).toBeInTheDocument()
  await userEvent.click(screen.getByRole('button', { name: 'Research' }))
  await waitFor(() => expect(fetchMock.mock.calls.some(([url]) => String(url).includes('category=research'))).toBe(true))
})

test('unknown routes render the polished 404', () => {
  mockApi(); renderApp('/missing-page')
  expect(screen.getByRole('heading', { name: 'This page wandered off' })).toBeInTheDocument()
  expect(screen.getByRole('link', { name: 'Return to MediVita' })).toHaveAttribute('href', '/chat')
})
