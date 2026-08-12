import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { expect, test, vi } from 'vitest'
import { Toggle } from '../src/components/ui/Toggle'

test('enabled switch exposes a stable on state', () => {
  render(<Toggle checked onChange={() => undefined} label="Disable Mayo Clinic" />)
  const toggle = screen.getByRole('switch', { name: 'Disable Mayo Clinic' })
  expect(toggle).toHaveAttribute('aria-checked', 'true')
  expect(toggle).toHaveAttribute('data-state', 'on')
  expect(toggle).toHaveClass('overflow-hidden')
})

test('disabled switch exposes a stable off state', () => {
  render(<Toggle checked={false} onChange={() => undefined} label="Enable Mayo Clinic" />)
  const toggle = screen.getByRole('switch', { name: 'Enable Mayo Clinic' })
  expect(toggle).toHaveAttribute('aria-checked', 'false')
  expect(toggle).toHaveAttribute('data-state', 'off')
})

test('the full accessible switch target activates its callback', async () => {
  const onChange = vi.fn()
  render(<Toggle checked onChange={onChange} label="Disable Mayo Clinic" />)
  await userEvent.click(screen.getByRole('switch', { name: 'Disable Mayo Clinic' }))
  expect(onChange).toHaveBeenCalledOnce()
})
