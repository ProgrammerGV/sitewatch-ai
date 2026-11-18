import { useEffect, useRef, useState } from 'react'
import { api } from '../api'
import type { Occurrence, ReviewDecision, Source, View } from '../types'
import { useFeedback } from './useFeedback'
import { useHealth } from './useHealth'
import { useMonitor } from './useMonitor'
import { useOccurrenceHistory } from './useOccurrenceHistory'

/** Compose application actions; pages receive data and callbacks, never fetch directly. */
export function useDashboard() {
  const [view, setView] = useState<View>('monitor')
  const [source, setSource] = useState<Source | null>(null)
  const [filter, setFilter] = useState('')
  const [page, setPage] = useState(1)
  const [detail, setDetail] = useState<Occurrence | null>(null)
  const [note, setNote] = useState('')
  const [decision, setDecision] = useState<ReviewDecision>('person_present')
  const detailRequest = useRef(0)
  const feedback = useFeedback()
  const monitor = useMonitor()
  const health = useHealth()
  const history = useOccurrenceHistory(filter, page, feedback.reportError)
  const active = ['starting', 'running', 'stopping'].includes(monitor.status.state)

  useEffect(() => {
    const controller = new AbortController()
    api<Source>('/source', 'GET', undefined, controller.signal)
      .then((value) => {
        if (!controller.signal.aborted) setSource(value)
      })
      .catch((error) => {
        if (!controller.signal.aborted) feedback.reportError(error)
      })
    return () => controller.abort()
  }, [feedback.reportError])

  const navigate = (next: View) => {
    if (next !== 'settings') {
      setFilter('')
      setPage(1)
    }
    setView(next)
  }
  const control = (command: 'start' | 'stop') => {
    void feedback.run(() => monitor.control(command))
  }
  const openOccurrence = (id: string) => {
    const request = ++detailRequest.current
    void feedback.run(async () => {
      const value = await api<Occurrence>(`/occurrences/${id}`)
      if (request !== detailRequest.current) return
      setDetail(value)
      setNote('')
      setDecision('person_present')
    })
  }
  const closeOccurrence = () => {
    detailRequest.current++
    setDetail(null)
  }
  const saveSource = () => {
    if (!source) return
    void feedback.run(
      async () => setSource(await api<Source>('/source', 'PATCH', source)),
      'Configuration saved for the next session.',
    )
  }
  const saveReview = () => {
    if (!detail) return
    const occurrenceId = detail.id
    const request = detailRequest.current
    void feedback.run(async () => {
      await api(`/occurrences/${occurrenceId}/reviews`, 'POST', { decision, note })
      const value = await api<Occurrence>(`/occurrences/${occurrenceId}`)
      if (request === detailRequest.current) {
        setDetail(value)
        setNote('')
      }
      await history.refresh()
    }, 'Review saved. Automatic classification preserved.')
  }

  return {
    view,
    source,
    setSource,
    filter,
    setFilter,
    page,
    setPage,
    detail,
    note,
    setNote,
    decision,
    setDecision,
    feedback,
    active,
    navigate,
    control,
    openOccurrence,
    closeOccurrence,
    saveSource,
    saveReview,
    events: history.events,
    status: monitor.status,
    connected: monitor.connected,
    ...health,
  }
}
