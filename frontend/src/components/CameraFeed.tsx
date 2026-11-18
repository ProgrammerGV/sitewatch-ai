import { Camera, Circle, Maximize } from 'lucide-react'
import type { MonitorStatus, Source } from '../types'

export function CameraFeed({
  status,
  source,
  active,
}: {
  status: MonitorStatus
  source: Source | null
  active: boolean
}) {
  return (
    <section className="panel camera-panel">
      <div className="panel-heading">
        <div>
          <Camera size={18} />
          <h2>{source?.name || 'Notebook webcam'}</h2>
        </div>
        <span className={`feed-status ${status.state === 'running' ? 'live' : ''}`}>
          <Circle size={7} fill="currentColor" />
          {status.state === 'running' ? 'LIVE' : status.state.toUpperCase()}
        </span>
      </div>
      <div className="camera-view">
        {status.processed_frames > 0 ? (
          <>
            <img
              className="live-feed"
              src="/api/monitor/stream"
              alt="Camera view annotated with people and monitored region"
            />
            <div className="feed-overlay">
              <span>
                <span className="tiny-dot" />
                {active ? 'LOCAL ANALYSIS' : 'LAST CAPTURED FRAME'}
              </span>
              <span>{status.people} PEOPLE</span>
            </div>
          </>
        ) : (
          <div className="camera-empty">
            <div className="viewfinder">
              <Camera size={34} strokeWidth={1.2} />
              <span />
              <span />
              <span />
              <span />
            </div>
            <h3>
              {status.state === 'starting' ? 'Preparing your session' : 'Ready when you are.'}
            </h3>
            <p>
              {status.state === 'starting'
                ? 'Loading the detector and connecting to your camera.'
                : 'Start monitoring to see your camera and live detections.'}
            </p>
            <span className="camera-empty-label">ONE CAMERA. EVERY SIGNAL IN CONTEXT.</span>
          </div>
        )}
        <span className="camera-corner">
          <Maximize size={16} />
        </span>
      </div>
      <div className="camera-footer">
        <span>
          <span className="legend-person" />
          Person detected
        </span>
        <span>
          <span className="legend-region" />
          Monitored region
        </span>
        <span className="camera-footer-right">{status.processed_frames} frames analyzed</span>
      </div>
    </section>
  )
}
