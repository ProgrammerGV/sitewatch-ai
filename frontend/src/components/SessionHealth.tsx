import { Activity, ShieldCheck } from 'lucide-react'
import type { MonitorStatus } from '../types'

export function SessionHealth({
  status,
  active,
  dbOk,
  modelOk,
}: {
  status: MonitorStatus
  active: boolean
  dbOk: boolean
  modelOk: boolean
}) {
  return (
    <section className="panel session-panel">
      <div className="panel-heading">
        <div>
          <Activity size={17} />
          <h2>Session health</h2>
        </div>
      </div>
      <div className="health-row">
        <span>Video pipeline</span>
        <strong>
          <span className={`tiny-dot ${status.state === 'running' ? '' : 'muted'}`} />
          {status.state === 'running'
            ? 'Running'
            : status.state === 'error'
              ? 'Interrupted'
              : active
                ? 'Starting'
                : 'Idle'}
        </strong>
      </div>
      <div className="health-row">
        <span>PostgreSQL</span>
        <strong>
          <span className={`tiny-dot ${dbOk ? '' : 'muted'}`} />
          {dbOk ? 'Connected' : 'Unavailable'}
        </strong>
      </div>
      <div className="health-row">
        <span>Detection model</span>
        <strong>
          <span className={`tiny-dot ${modelOk ? '' : 'muted'}`} />
          {modelOk ? 'Available' : 'Not downloaded'}
        </strong>
      </div>
      <div className="health-row">
        <span>Processing</span>
        <strong>On this computer</strong>
      </div>
      <div className="session-foot">
        <ShieldCheck size={15} />
        Evidence is stored locally.
      </div>
    </section>
  )
}
