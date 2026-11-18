import { ChevronLeft, ChevronRight, History } from 'lucide-react'
import type { Page } from '../types'
import { OccurrenceList } from '../components/OccurrenceList'

export function HistoryPage({
  events,
  filter,
  page,
  onFilterChange,
  onPageChange,
  onOpenOccurrence,
}: {
  events: Page
  filter: string
  page: number
  onFilterChange: (value: string) => void
  onPageChange: (page: number) => void
  onOpenOccurrence: (id: string) => void
}) {
  return (
    <section className="panel">
      <div className="panel-heading history-heading">
        <div>
          <History size={18} />
          <h2>Occurrence log</h2>
          <span className="subtle-count">{events.total}</span>
        </div>
        <label className="filter-label">
          Result
          <select
            value={filter}
            onChange={(e) => {
              onFilterChange(e.target.value)
              onPageChange(1)
            }}
          >
            <option value="">All results</option>
            <option value="person_detected">Person detected</option>
            <option value="no_person_detected">No person detected</option>
            <option value="inconclusive">Inconclusive</option>
          </select>
        </label>
      </div>
      <OccurrenceList events={events} onOpen={onOpenOccurrence} />
      <div className="pagination">
        <span>
          Page {page} · {events.total} occurrences
        </span>
        <div>
          <button
            aria-label="Previous page"
            disabled={page === 1}
            onClick={() => onPageChange(page - 1)}
          >
            <ChevronLeft size={16} />
          </button>
          <button
            aria-label="Next page"
            disabled={page * 20 >= events.total}
            onClick={() => onPageChange(page + 1)}
          >
            <ChevronRight size={16} />
          </button>
        </div>
      </div>
    </section>
  )
}
