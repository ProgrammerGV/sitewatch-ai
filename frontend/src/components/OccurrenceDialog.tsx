import { Check, Clock3, X } from 'lucide-react'
import { date, labels } from '../presentation'
import type { Occurrence, ReviewDecision } from '../types'
import { Badge } from './Badge'

export function OccurrenceDialog({
  detail,
  busy,
  note,
  decision,
  onClose,
  onNoteChange,
  onDecisionChange,
  onSave,
}: {
  detail: Occurrence
  busy: boolean
  note: string
  decision: ReviewDecision
  onClose: () => void
  onNoteChange: (note: string) => void
  onDecisionChange: (decision: ReviewDecision) => void
  onSave: () => void
}) {
  return (
    <div
      className="modal-backdrop"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose()
      }}
    >
      <section
        className="modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="detail-title"
        onKeyDown={(e) => {
          if (e.key === 'Escape') onClose()
        }}
      >
        <div className="modal-heading">
          <div>
            <div className="eyebrow">OCCURRENCE DETAILS</div>
            <h2 id="detail-title">Review the evidence.</h2>
          </div>
          <button
            className="icon-button"
            aria-label="Close details"
            onClick={() => onClose()}
            autoFocus
          >
            <X size={22} />
          </button>
        </div>
        <div className="detail-summary">
          <Badge value={detail.classification} />
          <span>
            <Clock3 size={14} />
            {date(detail.started_at)}
          </span>
          <span>{detail.status}</span>
        </div>
        <div className="detail-images">
          {detail.evidence?.map((e) => (
            <figure key={e.id}>
              <img src={`/api/evidence/${e.id}`} alt={`${e.kind} occurrence evidence`} />
              <figcaption>
                {e.kind} · {date(e.captured_at)}
              </figcaption>
            </figure>
          ))}
        </div>
        <div className="detail-metrics">
          <div>
            <strong>{detail.peak_people}</strong>
            <span>Peak people in region</span>
          </div>
          <div>
            <strong>{detail.summary.valid_samples || 0}</strong>
            <span>Successful analyses</span>
          </div>
          <div>
            <strong>{detail.summary.max_analysis_gap_seconds?.toFixed(2) || '0'}s</strong>
            <span>Largest analysis gap</span>
          </div>
        </div>
        <h3>Human review</h3>
        <p className="field-help">
          Record what you can verify in the evidence. Your review does not overwrite the automatic
          result.
        </p>
        <label className="review-decision">
          Decision
          <select
            disabled={detail.status === 'active'}
            value={decision}
            onChange={(e) => onDecisionChange(e.target.value as ReviewDecision)}
          >
            <option value="person_present">Person present</option>
            <option value="no_person">No person visible</option>
            <option value="uncertain">Uncertain</option>
          </select>
        </label>
        <textarea
          aria-label="Review notes"
          value={note}
          onChange={(e) => onNoteChange(e.target.value)}
          maxLength={2000}
          placeholder="Add context, limitations, or anything the detector missed…"
          disabled={detail.status === 'active'}
        />
        <button
          className="button primary"
          disabled={busy || detail.status === 'active'}
          onClick={() => onSave()}
        >
          <Check size={16} />
          {detail.status === 'active' ? 'Wait for occurrence to close' : 'Save review'}
        </button>
        {detail.reviews?.map((review) => (
          <div className="review-entry" key={review.id}>
            <strong>{labels[review.decision]}</strong>
            <span>{date(review.created_at)}</span>
            <p>{review.note || 'No additional notes.'}</p>
          </div>
        ))}
        <details>
          <summary>Analysis observations ({detail.observations?.length || 0} most recent)</summary>
          <div className="observations">
            {detail.observations?.map((o) => (
              <div key={o.id}>
                <span>{date(o.captured_at)}</span>
                <span>{o.person_count} people</span>
                <span>{(o.motion_score * 100).toFixed(1)}% motion</span>
              </div>
            ))}
          </div>
        </details>
        <small className="event-id">ID {detail.id}</small>
      </section>
    </div>
  )
}
