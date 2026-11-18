import { Check, Crosshair, Database, Settings2 } from 'lucide-react'
import type { Source } from '../types'
import { RegionEditor } from '../components/RegionEditor'

export function SettingsPage({
  source,
  onSourceChange,
  onSave,
  active,
  busy,
  hasFrame,
}: {
  source: Source | null
  onSourceChange: (source: Source) => void
  onSave: () => void
  active: boolean
  busy: boolean
  hasFrame: boolean
}) {
  return (
    <div className="settings-grid">
      <section className="panel">
        <div className="panel-heading">
          <div>
            <Crosshair size={18} />
            <h2>Monitored region</h2>
          </div>
          <button
            className="text-button"
            disabled={!source || active}
            onClick={() => source && onSourceChange({ ...source, roi: [0, 0, 1, 1] })}
          >
            Reset to full frame
          </button>
        </div>
        {source && (
          <RegionEditor
            roi={source.roi}
            hasFrame={hasFrame}
            change={(roi) => !active && onSourceChange({ ...source, roi })}
          />
        )}
        <p className="field-help">
          Stop monitoring, then drag to draw a rectangle. A person’s bottom-center point must be
          inside this area.
        </p>
      </section>
      <section className="panel settings-form">
        <div className="panel-heading">
          <div>
            <Settings2 size={18} />
            <h2>Detection settings</h2>
          </div>
        </div>
        {source ? (
          <form
            onSubmit={(e) => {
              e.preventDefault()
              onSave()
            }}
          >
            <fieldset disabled={active || busy}>
              <label>
                Source name
                <input
                  value={source.name}
                  maxLength={120}
                  required
                  onChange={(e) => onSourceChange({ ...source, name: e.target.value })}
                />
              </label>
              <label>
                Camera index
                <input
                  type="number"
                  min="0"
                  max="20"
                  value={source.camera_index}
                  onChange={(e) =>
                    onSourceChange({ ...source, camera_index: Number(e.target.value) })
                  }
                />
              </label>
              <label>
                Minimum confidence <span>{(source.confidence * 100).toFixed(0)}%</span>
                <input
                  type="range"
                  min="0.05"
                  max="1"
                  step="0.05"
                  value={source.confidence}
                  onChange={(e) =>
                    onSourceChange({ ...source, confidence: Number(e.target.value) })
                  }
                />
              </label>
              <p className="field-help">
                A model score, not a guaranteed probability of correctness.
              </p>
              <label>
                Motion threshold{' '}
                <span>{(source.motion_threshold * 100).toFixed(1)}% of region</span>
                <input
                  type="range"
                  min="0.001"
                  max="0.2"
                  step="0.001"
                  value={source.motion_threshold}
                  onChange={(e) =>
                    onSourceChange({ ...source, motion_threshold: Number(e.target.value) })
                  }
                />
              </label>
              <button className="button primary" type="submit">
                <Check size={16} />
                Save configuration
              </button>
            </fieldset>
            {active && <p className="field-help">Stop monitoring to edit configuration.</p>}
          </form>
        ) : (
          <div className="empty">
            <Database size={28} />
            <p>Connect PostgreSQL and run migrations to configure your source.</p>
            <code>sitewatch migrate</code>
          </div>
        )}
      </section>
    </div>
  )
}
