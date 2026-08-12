import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { expect, test, vi } from 'vitest'
import App from '../src/App'
import { ConversationProvider } from '../src/state/ConversationContext'
import { SourceProvider } from '../src/state/SourceContext'
import { ToastProvider } from '../src/state/ToastContext'
import type { Conversation } from '../src/types'

const STORAGE_KEY = 'medivita:conversations'
const ACTIVE_KEY = 'medivita:active-conversation'

function conversation(id: string, title: string, day = 0): Conversation {
  const createdAt = new Date(Date.now() - day * 86_400_000).toISOString()
  return {
    id,
    title,
    updatedAt: createdAt,
    messages: [{ id: `${id}-message`, role: 'user', content: `${title} message`, createdAt }],
  }
}

function seed(conversations = [conversation('active', 'Active conversation'), conversation('other', 'Other conversation', 1)], activeId = 'active') {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(conversations))
  localStorage.setItem(ACTIVE_KEY, activeId)
}

function mockApi() {
  vi.spyOn(globalThis, 'fetch').mockResolvedValue({ ok: true, json: () => Promise.resolve({ articles: [], mode: 'demo' }) } as Response)
}

function renderApp() {
  mockApi()
  return render(
    <MemoryRouter initialEntries={['/chat']}>
      <ToastProvider><SourceProvider><ConversationProvider><App /></ConversationProvider></SourceProvider></ToastProvider>
    </MemoryRouter>,
  )
}

async function openMenu(title: string) {
  const trigger = screen.getByRole('button', { name: `Conversation options for ${title}` })
  await userEvent.click(trigger)
  return screen.getByRole('menu', { name: `Actions for ${title}` })
}

test('conversation menu is keyboard accessible and closes with Escape or an outside press', async () => {
  seed(); renderApp()
  const trigger = screen.getByRole('button', { name: 'Conversation options for Active conversation' })
  trigger.focus()
  await userEvent.keyboard('{Enter}')
  const menu = screen.getByRole('menu', { name: 'Actions for Active conversation' })
  expect(within(menu).getByRole('menuitem', { name: 'Rename' })).toHaveFocus()
  expect(within(menu).getByRole('menuitem', { name: 'Delete' })).toBeInTheDocument()

  await userEvent.keyboard('{Escape}')
  expect(screen.queryByRole('menu')).not.toBeInTheDocument()
  await waitFor(() => expect(trigger).toHaveFocus())

  await userEvent.click(trigger)
  fireEvent.pointerDown(document.body)
  expect(screen.queryByRole('menu')).not.toBeInTheDocument()
})

test('rename is prepopulated, constrained, and Escape cancels without changing storage', async () => {
  seed(); renderApp()
  const menu = await openMenu('Active conversation')
  await userEvent.click(within(menu).getByRole('menuitem', { name: 'Rename' }))
  const input = screen.getByRole('textbox', { name: 'Rename Active conversation' })
  expect(input).toHaveValue('Active conversation')
  expect(input).toHaveAttribute('maxlength', '100')
  expect(input).toHaveFocus()
  await userEvent.type(input, ' changed')
  await userEvent.keyboard('{Escape}')
  expect(screen.getByText('Active conversation')).toBeInTheDocument()
  expect(JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]')[0].title).toBe('Active conversation')
})

test('Enter saves a trimmed manual title and it persists across remounts', async () => {
  seed()
  const first = renderApp()
  const menu = await openMenu('Active conversation')
  await userEvent.click(within(menu).getByRole('menuitem', { name: 'Rename' }))
  const input = screen.getByRole('textbox', { name: 'Rename Active conversation' })
  await userEvent.clear(input)
  await userEvent.type(input, '  A lasting manual title  ')
  expect(input).toHaveValue('  A lasting manual title  ')
  expect(input).toHaveFocus()
  await userEvent.keyboard('{Enter}')
  expect(JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]')[0].title).toBe('A lasting manual title')
  expect(await screen.findByText('A lasting manual title')).toBeInTheDocument()

  first.unmount()
  renderApp()
  expect(screen.getByRole('button', { name: 'Conversation options for A lasting manual title' })).toBeInTheDocument()
})

test('blank rename is rejected and keeps the previous title', async () => {
  seed(); renderApp()
  const menu = await openMenu('Active conversation')
  await userEvent.click(within(menu).getByRole('menuitem', { name: 'Rename' }))
  const input = screen.getByRole('textbox', { name: 'Rename Active conversation' })
  await userEvent.clear(input)
  await userEvent.type(input, '   ')
  await userEvent.keyboard('{Enter}')
  expect(screen.getByText('Active conversation')).toBeInTheDocument()
  expect(JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]')[0].title).toBe('Active conversation')
})

test('delete requires confirmation and Cancel preserves the conversation', async () => {
  seed(); renderApp()
  const trigger = screen.getByRole('button', { name: 'Conversation options for Other conversation' })
  const menu = await openMenu('Other conversation')
  await userEvent.click(within(menu).getByRole('menuitem', { name: 'Delete' }))
  const dialog = screen.getByRole('dialog', { name: 'Delete conversation?' })
  expect(within(dialog).getByText(/Other conversation/)).toBeInTheDocument()
  await waitFor(() => expect(within(dialog).getByRole('button', { name: 'Cancel' })).toHaveFocus())
  await userEvent.click(within(dialog).getByRole('button', { name: 'Cancel' }))
  expect(screen.queryByRole('dialog', { name: 'Delete conversation?' })).not.toBeInTheDocument()
  expect(screen.getByText('Other conversation')).toBeInTheDocument()
  await waitFor(() => expect(trigger).toHaveFocus())
})

test('deleting an inactive conversation preserves the active conversation and ordering', async () => {
  const stored = [conversation('active', 'Active conversation'), conversation('other', 'Other conversation'), conversation('last', 'Last conversation')]
  seed(stored); renderApp()
  const menu = await openMenu('Other conversation')
  await userEvent.click(within(menu).getByRole('menuitem', { name: 'Delete' }))
  const dialog = screen.getByRole('dialog', { name: 'Delete conversation?' })
  await userEvent.click(within(dialog).getByRole('button', { name: 'Delete' }))

  expect(screen.queryByText('Other conversation')).not.toBeInTheDocument()
  expect(screen.getByText('Active conversation message')).toBeInTheDocument()
  expect(localStorage.getItem(ACTIVE_KEY)).toBe('active')
  expect(JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]').map((item: Conversation) => item.id)).toEqual(['active', 'last'])
})

test('deleting the active conversation opens a fresh empty chat', async () => {
  seed(); renderApp()
  const menu = await openMenu('Active conversation')
  await userEvent.click(within(menu).getByRole('menuitem', { name: 'Delete' }))
  const dialog = screen.getByRole('dialog', { name: 'Delete conversation?' })
  await userEvent.click(within(dialog).getByRole('button', { name: 'Delete' }))

  expect(localStorage.getItem(ACTIVE_KEY)).toBeNull()
  expect(JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]').map((item: Conversation) => item.id)).toEqual(['other'])
  expect(screen.getByRole('heading', { name: 'How can I help you explore your health question?' })).toBeInTheDocument()
})

test('existing stored records and long histories retain actions and an independent scroll region', () => {
  const existingRecords = Array.from({ length: 24 }, (_, index) => conversation(`legacy-${index}`, `Stored conversation ${index + 1}`, index))
  seed(existingRecords, 'legacy-0'); renderApp()
  expect(screen.getAllByRole('button', { name: /Conversation options for Stored conversation/ })).toHaveLength(24)
  expect(screen.getByTestId('conversation-scroll')).toHaveClass('overflow-y-auto')
  expect(screen.getByTestId('conversation-scroll')).not.toContainElement(screen.getByTestId('privacy-footer'))
})

test('mobile navigation exposes an explicit conversation action trigger', async () => {
  seed(); renderApp()
  await userEvent.click(screen.getByRole('button', { name: 'Open navigation' }))
  const drawer = screen.getByRole('dialog', { name: 'Navigation' })
  const trigger = within(drawer).getByRole('button', { name: 'Conversation options for Active conversation' })
  expect(trigger).toHaveAttribute('aria-haspopup', 'menu')
  await userEvent.click(trigger)
  expect(screen.getByRole('menu', { name: 'Actions for Active conversation' })).toBeInTheDocument()
})
