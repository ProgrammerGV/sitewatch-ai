import { SessionHealth } from '../components/SessionHealth'
import { CameraFeed } from '../components/CameraFeed'
import { LiveMetrics } from '../components/LiveMetrics'
import { ArrowRight, Eye, History } from 'lucide-react'
import type { MonitorStatus, Page, Source } from '../types'
import { OccurrenceList } from '../components/OccurrenceList'

export function MonitorPage({
  status,
  source,
  active,
  dbOk,
  modelOk,
  events,
  onViewHistory,
  onOpenOccurrence,
}: {
  status: MonitorStatus
  source: Source | null
  active: boolean
  dbOk: boolean
  modelOk: boolean
  events: Page
  onViewHistory: () => void
  onOpenOccurrence: (id: string) => void
}) {
  return (
    <>
      <LiveMetrics status={status} active={active} occurrenceCount={events.total} />
      <div className="monitor-layout">
        <CameraFeed status={status} source={source} active={active} />
        <aside className="right-column">
          <SessionHealth status={status} active={active} dbOk={dbOk} modelOk={modelOk} />
          <section className="insight-card">
            <div className="insight-label">
              <Eye size={19} />A SIGNAL ISN’T A VERDICT
            </div>
            <h3>
              Movement doesn’t
              <br />
              always mean a person.
            </h3>
            <p>
              Motion and AI run independently. A person standing still can still be detected. An
              uncertain analysis stays uncertain.
            </p>
            <button onClick={onViewHistory}>
              Review your occurrences <ArrowRight size={16} />
            </button>
          </section>
        </aside>
      </div>
      <section className="panel recent-panel">
        <div className="panel-heading">
          <div>
            <History size={17} />
            <h2>Recent occurrences</h2>
            <span className="subtle-count">{events.total}</span>
          </div>
          <button className="text-button" onClick={onViewHistory}>
            View history <ArrowRight size={15} />
          </button>
        </div>
        <OccurrenceList events={events} onOpen={onOpenOccurrence} compact />
      </section>
    </>
  )
}
