import { render, screen } from '@testing-library/react'
import { expect, test } from 'vitest'
import { AssistantResponse } from '../src/features/chat/AssistantResponse'
import type { ChatResponse } from '../src/types'


function response(overrides: Partial<ChatResponse>): ChatResponse {
  return {
    answer: 'Hello! How can I help?',
    sections: [{ title: 'Response', content: 'Hello! How can I help?' }],
    sources: [],
    safety_notice: null,
    mode: 'connected',
    disclaimer: 'General health information only.',
    ...overrides,
  }
}


test('direct connected response does not imply research or render sources', () => {
  render(<AssistantResponse response={response({ response_kind: 'direct' })} />)
  expect(screen.getByText('Direct response')).toBeInTheDocument()
  expect(screen.queryByText('Researched response')).not.toBeInTheDocument()
  expect(screen.queryByRole('heading', { name: 'Sources' })).not.toBeInTheDocument()
})


test('clarification uses a clear response label and no source block', () => {
  render(<AssistantResponse response={response({
    response_kind: 'clarification',
    answer: 'Which symptom do you mean?',
    sections: [{ title: 'A quick question', content: 'Which symptom do you mean?' }],
  })} />)
  expect(screen.getByText('Clarifying question')).toBeInTheDocument()
  expect(screen.getByText('Which symptom do you mean?')).toBeInTheDocument()
  expect(screen.queryByRole('heading', { name: 'Sources' })).not.toBeInTheDocument()
})
