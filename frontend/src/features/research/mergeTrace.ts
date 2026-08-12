import type { ResearchTraceEvent } from '../../types/research'

export function mergeTraceEvent(
  events: ResearchTraceEvent[],
  incoming: ResearchTraceEvent,
): ResearchTraceEvent[] {
  const index = events.findIndex((event) => event.id === incoming.id)
  if (index < 0) return [...events, incoming]
  return events.map((event, itemIndex) => itemIndex === index ? incoming : event)
}
