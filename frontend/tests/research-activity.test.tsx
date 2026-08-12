import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { expect, test } from 'vitest'
import { ResearchActivity } from '../src/features/research/ResearchActivity'
import type { ResearchSummary, ResearchTraceEvent } from '../src/types'

const summary: ResearchSummary = {
  rounds: 1,
  evidence_count: 4,
  citation_count: 3,
  total_ms: 1730,
}

const events: ResearchTraceEvent[] = [
  { id: 'safety-1', stage: 'safety', status: 'completed', label: 'Safety screening complete', tool: 'Deterministic safety rules' },
  { id: 'search-1', stage: 'search', status: 'completed', label: 'Mayo Clinic search complete', tool: 'DDGS Search', source_id: 'mayo-clinic', source_name: 'Mayo Clinic', backend: 'bing', query: 'site:mayoclinic.org migraine symptoms', result_count: 2, round: 1 },
  { id: 'evidence-1', stage: 'evidence', status: 'completed', label: 'Relevant evidence selected', tool: 'MediVita Evidence Ranker', evidence_count: 4, round: 1 },
  { id: 'generation-1', stage: 'generation', status: 'completed', label: 'Grounded generation complete', tool: 'LangChain structured generation', provider: 'groq', model: 'openai/gpt-oss-20b', elapsed_ms: 920, round: 1 },
  { id: 'citation-1', stage: 'citation', status: 'completed', label: 'Trusted citations prepared', tool: 'MediVita Citation Mapper', citation_count: 3, round: 1 },
]

test('completed research is compact, friendly first, and technical on demand', async () => {
  render(<ResearchActivity events={events} summary={summary} />)
  const detailsToggle = screen.getByRole('button', { name: /Research complete/ })
  expect(detailsToggle).toHaveAttribute('aria-expanded', 'false')
  expect(screen.queryByText(/migraine symptoms/)).not.toBeInTheDocument()

  await userEvent.click(detailsToggle)
  expect(detailsToggle).toHaveAttribute('aria-expanded', 'true')
  expect(screen.getByText(/Searched:.*migraine symptoms/)).toBeInTheDocument()
  expect(screen.queryByText(/site:mayoclinic\.org/)).not.toBeInTheDocument()
  expect(screen.queryByText(/DDGS Search/)).not.toBeInTheDocument()
  expect(screen.getByText('Selected 4 relevant pieces of information')).toBeInTheDocument()

  const technicalToggle = screen.getByRole('button', { name: /Details/ })
  await userEvent.click(technicalToggle)
  expect(technicalToggle).toHaveAttribute('aria-expanded', 'true')
  expect(screen.getByText(/site:mayoclinic\.org migraine symptoms/)).toBeInTheDocument()
  expect(screen.getByText(/DDGS Search.*Mayo Clinic.*Bing.*2 results/)).toBeInTheDocument()
  expect(screen.getByText(/Groq.*openai\/gpt-oss-20b/)).toBeInTheDocument()
  expect(screen.getByText(/MediVita Citation Mapper.*3 trusted links/)).toBeInTheDocument()
})

test('running research stays open and uses natural-language progress', () => {
  render(<ResearchActivity events={[{ ...events[1], status: 'running', label: 'Searching Mayo Clinic' }]} running />)
  expect(screen.getByRole('button', { name: /Searching trusted health sources/ })).toHaveAttribute('aria-expanded', 'true')
  expect(screen.getByText('Searching trusted health sources')).toBeInTheDocument()
  expect(screen.getByText(/Searched:.*migraine symptoms/)).toBeInTheDocument()
  expect(screen.queryByText(/site:mayoclinic\.org/)).not.toBeInTheDocument()
})

test('round two is described naturally while exact metadata stays technical', async () => {
  const secondRound = { ...events[1], id: 'search-2', round: 2, query: 'site:mayoclinic.org migraine warning signs' }
  render(<ResearchActivity events={[...events, secondRound]} summary={{ ...summary, rounds: 2 }} initiallyExpanded />)
  expect(screen.getByText('Looking for a little more information')).toBeInTheDocument()
  expect(screen.getByText(/Searched:.*migraine warning signs/)).toBeInTheDocument()
  expect(screen.queryByText('Round 2')).not.toBeInTheDocument()

  await userEvent.click(screen.getByRole('button', { name: /Details/ }))
  expect(screen.getByText('Round 2')).toBeInTheDocument()
  expect(screen.getByText(/site:mayoclinic\.org migraine warning signs/)).toBeInTheDocument()
})

test('demo trace clearly says no external research was used', () => {
  render(<ResearchActivity
    events={[{ id: 'complete-1', stage: 'complete', status: 'completed', label: 'Demo mode', tool: 'Deterministic response', message: 'No external tools called' }]}
    summary={{ rounds: 0, evidence_count: 0, citation_count: 0, total_ms: 1 }}
    initiallyExpanded
  />)
  expect(screen.getByRole('button', { name: /Demo response.*no external research/ })).toBeInTheDocument()
  expect(screen.getByText(/deterministic demo content/)).toBeInTheDocument()
  expect(screen.queryByText(/DDGS|Groq/)).not.toBeInTheDocument()
  expect(screen.queryByRole('button', { name: /Details/ })).not.toBeInTheDocument()
})

test('no panel is rendered for old responses without trace data', () => {
  const { container } = render(<ResearchActivity />)
  expect(container).toBeEmptyDOMElement()
})
