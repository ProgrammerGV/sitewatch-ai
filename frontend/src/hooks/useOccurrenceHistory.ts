import { useCallback, useEffect, useRef, useState } from 'react'
import { api } from '../api'
import type { Page } from '../types'
import { usePollingTask } from './usePollingTask'

const EMPTY_PAGE: Page = { items: [], total: 0, page: 1, page_size: 20 }

export function useOccurrenceHistory(
  filter: string,
  page: number,
  onError: (error: unknown) => void,
) {
  const [events, setEvents] = useState<Page>(EMPTY_PAGE)
  const requestSequence = useRef(0)
  const refresh = useCallback(
    async (signal?: AbortSignal) => {
      const sequence = ++requestSequence.current
      const query = new URLSearchParams({ page: String(page) })
      if (filter) query.set('classification', filter)
      const result = await api<Page>(`/occurrences?${query}`, 'GET', undefined, signal)
      if (!signal?.aborted && sequence === requestSequence.current) setEvents(result)
    },
    [page, filter],
  )

  const poll = useCallback(
    async (signal: AbortSignal) => {
      try {
        await refresh(signal)
      } catch (error) {
        if (!signal.aborted) onError(error)
      }
    },
    [refresh, onError],
  )
  usePollingTask(poll, 5000)
  useEffect(
    () => () => {
      requestSequence.current++
    },
    [],
  )
  return { events, refresh }
}
