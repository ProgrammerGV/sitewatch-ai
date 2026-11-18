import { ChevronRight, History, Scan } from 'lucide-react'
import { date } from '../presentation'
import type { Page } from '../types'
import { Badge } from './Badge'

export function OccurrenceList({
  events,
  onOpen,
  compact = false,
}: {
  events: Page
  onOpen: (id: string) => void
  compact?: boolean
}) {
  return (
    <div className="event-list">
      {events.items.length === 0 ? (
        <div className="empty">
          <History size={30} />
          <h3>Your history starts here</h3>
          <p>Start a session. Motion or human presence in your region will create an occurrence.</p>
        </div>
      ) : (
        events.items.slice(0, compact ? 4 : 20).map((event) => (
          <button className="event-row" key={event.id} onClick={() => onOpen(event.id)}>
            <div className={`event-thumb ${event.classification}`}>
              {event.evidence_id ? (
                <img src={`/api/evidence/${event.evidence_id}`} alt="Occurrence evidence" />
              ) : (
                <Scan size={22} />
              )}
            </div>
            <div className="event-copy">
              <strong>
                {event.classification === 'person_detected'
                  ? 'Human presence in region'
                  : event.classification === 'no_person_detected'
                    ? 'Motion without a detected person'
                    : 'Analysis needs attention'}
              </strong>
              <span>
                {date(event.started_at)} <i>·</i> {event.status}
              </span>
            </div>
            <div className="event-meta">
              <Badge value={event.classification} />
              <small>{event.review ? 'Reviewed' : 'Awaiting review'}</small>
            </div>
            <ChevronRight size={17} />
          </button>
        ))
      )}
    </div>
  )
}
