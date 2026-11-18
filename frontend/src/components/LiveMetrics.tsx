import { Activity, ArrowRight, History, Radar, Users } from 'lucide-react'
import type { MonitorStatus } from '../types'

export function LiveMetrics({
  status,
  active,
  occurrenceCount,
}: {
  status: MonitorStatus
  active: boolean
  occurrenceCount: number
}) {
  return (
    <section className="stats" aria-label="Live monitoring metrics">
      <div className="stat">
        <span className="stat-label">
          PEOPLE VISIBLE <Users size={17} />
        </span>
        <div className="stat-value">
          {status.people.toString().padStart(2, '0')}
          <span className="stat-tag">LIVE COUNT</span>
        </div>
        <p>{status.people_in_region} inside the monitored region</p>
      </div>
      <div className="stat">
        <span className="stat-label">
          MOTION SIGNAL <Activity size={17} />
        </span>
        <div className={`stat-word ${status.motion ? 'accent' : ''}`}>
          {active
            ? status.warming_up
              ? 'Adapting'
              : status.motion
                ? 'Detected'
                : 'Quiet'
            : 'Standby'}
          <span className="signal-bars">
            <i />
            <i />
            <i />
            <i />
          </span>
        </div>
        <p>Independent of human presence</p>
      </div>
      <div className="stat">
        <span className="stat-label">
          ANALYSIS SPEED <Radar size={17} />
        </span>
        <div className="stat-value">
          {status.analysis_fps.toFixed(1)}
          <span className="unit">fps</span>
        </div>
        <p>
          {status.inference_ms.toFixed(0)} ms inference · {status.frame_age_ms.toFixed(0)} ms frame
          age
        </p>
      </div>
      <div className="stat">
        <span className="stat-label">
          OCCURRENCES <History size={17} />
        </span>
        <div className="stat-value">
          {occurrenceCount.toString().padStart(2, '0')}
          <ArrowRight size={21} />
        </div>
        <p>
          {status.occurrence_id
            ? 'An occurrence is currently active'
            : 'Grouped events, ready for review'}
        </p>
      </div>
    </section>
  )
}
