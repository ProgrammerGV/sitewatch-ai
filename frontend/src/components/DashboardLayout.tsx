import type { ReactNode } from 'react'
import {
  Activity,
  ArrowDownLeft,
  Check,
  ChevronRight,
  ExternalLink,
  FileText,
  History,
  LayoutDashboard,
  LoaderCircle,
  Pause,
  Play,
  Scan,
  Settings2,
  ShieldCheck,
  X,
} from 'lucide-react'
import type { MonitorStatus, View } from '../types'

export function DashboardLayout({
  children,
  view,
  eventCount,
  connection,
  dbOk,
  status,
  active,
  busy,
  error,
  notice,
  onNavigate,
  onControl,
  onDismissError,
}: {
  children: ReactNode
  view: View
  eventCount: number
  connection: boolean
  dbOk: boolean
  status: MonitorStatus
  active: boolean
  busy: boolean
  error: string
  notice: string
  onNavigate: (view: View) => void
  onControl: (command: 'start' | 'stop') => void
  onDismissError: () => void
}) {
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <a className="brand" href="#" onClick={() => onNavigate('monitor')}>
          <span className="brand-symbol">
            <Scan size={23} />
          </span>
          <span>
            SITEWATCH<span className="brand-ai">AI</span>
            <small>VIDEO INTELLIGENCE</small>
          </span>
        </a>
        <div className="workspace-label">
          WORKSPACE <span>01</span>
        </div>
        <nav aria-label="Main navigation">
          <button
            className={view === 'monitor' ? 'selected' : ''}
            onClick={() => onNavigate('monitor')}
          >
            <LayoutDashboard size={18} />
            Overview
            <span className="nav-dot" />
          </button>
          <button
            className={view === 'history' ? 'selected' : ''}
            onClick={() => onNavigate('history')}
          >
            <History size={18} />
            Occurrences<span className="nav-count">{eventCount}</span>
          </button>
          <button
            className={view === 'settings' ? 'selected' : ''}
            onClick={() => onNavigate('settings')}
          >
            <Settings2 size={18} />
            Configuration
          </button>
        </nav>
        <div className="sidebar-note">
          <ShieldCheck size={20} />
          <strong>Your footage stays here.</strong>
          <p>Inference, evidence, and history run locally on this computer.</p>
          <span>
            LOCAL-FIRST BY DESIGN <ArrowDownLeft size={13} />
          </span>
        </div>
        <a className="api-link" href="/docs" target="_blank" rel="noreferrer">
          <FileText size={17} />
          API documentation
          <ExternalLink size={13} />
        </a>
        <div className="profile">
          <div className="avatar">SW</div>
          <div>
            <strong>Local workspace</strong>
            <small>Portfolio edition · v0.1</small>
          </div>
          <span className="tiny-dot" />
        </div>
      </aside>

      <main>
        <header className="topbar">
          <div className="breadcrumb">
            Workspace <ChevronRight size={13} />
            <span>
              {view === 'monitor'
                ? 'Overview'
                : view === 'history'
                  ? 'Occurrences'
                  : 'Configuration'}
            </span>
          </div>
          <div className="topbar-right">
            <span className="local-pill">
              <span className={`tiny-dot ${connection && dbOk ? '' : 'muted'}`} />
              {connection ? 'Local environment' : 'Backend offline'}
            </span>
            <span className="edition">LEARNING LAB</span>
          </div>
        </header>
        <div className="content">
          <div className="page-heading">
            <div>
              <div className="eyebrow">SEE THE SIGNAL. UNDERSTAND THE EVENT.</div>
              <h1>
                {view === 'monitor'
                  ? 'A clearer view of your site.'
                  : view === 'history'
                    ? 'Every event, in context.'
                    : 'Define what matters.'}
              </h1>
              <p>
                {view === 'monitor'
                  ? 'Separate movement from human presence. Keep the evidence that matters.'
                  : view === 'history'
                    ? 'Explore the evidence and add a human review to the automatic result.'
                    : 'Configure the camera, region, and detection thresholds for your next session.'}
              </p>
            </div>
            {view !== 'settings' && (
              <button
                className={`button ${active ? 'secondary' : 'primary'}`}
                disabled={busy || !connection || status.state === 'stopping'}
                onClick={() => onControl(active ? 'stop' : 'start')}
              >
                {busy || status.state === 'starting' ? (
                  <LoaderCircle size={16} className="spin" />
                ) : active ? (
                  <Pause size={16} />
                ) : (
                  <Play size={16} />
                )}
                {active ? 'Stop monitoring' : 'Start monitoring'}
              </button>
            )}
          </div>
          {(!connection || error || status.error) && (
            <div className="alert" role="alert">
              <Activity size={18} />
              <span>
                {!connection
                  ? 'Cannot reach the backend. Start the Python service and retry.'
                  : error || status.error}
              </span>
              {error && (
                <button aria-label="Dismiss message" onClick={() => onDismissError()}>
                  <X size={16} />
                </button>
              )}
            </div>
          )}
          {notice && (
            <div className="toast" role="status">
              <Check size={16} />
              {notice}
            </div>
          )}

          {children}
          <footer className="page-footer">
            <span>
              <Scan size={14} />
              SITEWATCH AI <i>/</i> LOCAL VIDEO ANALYTICS
            </span>
            <span>Built to observe. Designed to explain.</span>
          </footer>
        </div>
      </main>
    </div>
  )
}
