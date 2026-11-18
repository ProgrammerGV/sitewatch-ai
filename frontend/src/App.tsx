import { useCallback, useEffect, useRef, useState } from 'react'
import type { PointerEvent } from 'react'
import { Activity, ArrowDownLeft, ArrowRight, Camera, Check, ChevronLeft, ChevronRight, Circle, Clock3, Crosshair, Database, ExternalLink, Eye, FileText, History, LayoutDashboard, LoaderCircle, Maximize, Pause, Play, Radar, Scan, Settings2, ShieldCheck, Users, X } from 'lucide-react'
import { api, date, labels } from './api'
import type { MonitorStatus, Occurrence, Page, Region, Source } from './api'

const initial: MonitorStatus = { state: 'idle', error: null, people: 0, people_in_region: 0, motion: false, motion_score: 0, warming_up: false, inference_ms: 0, frame_age_ms: 0, processed_frames: 0, analysis_fps: 0, occurrence_id: null, session_id: null }
const empty: Page = { items: [], total: 0, page: 1, page_size: 20 }

function Badge({ value }: { value: string }) { return <span className={`badge ${value}`}>{labels[value] || value}</span> }

function RegionEditor({ roi, change, hasFrame }: { roi: Region; change: (r: Region) => void; hasFrame: boolean }) {
  const element = useRef<HTMLDivElement>(null)
  const anchor = useRef<[number, number] | null>(null)
  const [ratio, setRatio] = useState(4 / 3)
  const point = (event: PointerEvent) => {
    const rect = element.current!.getBoundingClientRect()
    return [Math.max(0, Math.min(1, (event.clientX - rect.left) / rect.width)), Math.max(0, Math.min(1, (event.clientY - rect.top) / rect.height))] as [number, number]
  }
  return <div className="region-editor" ref={element} style={{ aspectRatio: ratio }}
    onPointerDown={e => { if (!hasFrame) return; anchor.current = point(e); e.currentTarget.setPointerCapture(e.pointerId) }}
    onPointerMove={e => { if (!anchor.current) return; const [x, y] = point(e); const [ax, ay] = anchor.current; change([Math.min(ax, x), Math.min(ay, y), Math.abs(ax - x), Math.abs(ay - y)]) }}
    onPointerUp={e => { if (!anchor.current) return; const [x, y] = point(e); const [ax, ay] = anchor.current; if (Math.abs(ax-x) < .01 || Math.abs(ay-y) < .01) change([0, 0, 1, 1]); anchor.current = null }}
    onPointerCancel={() => { anchor.current = null }}>
    {hasFrame ? <img src="/api/monitor/stream" alt="Last captured scene for region selection" draggable={false} onLoad={e => setRatio(e.currentTarget.naturalWidth / e.currentTarget.naturalHeight)} /> : <div className="region-hint"><Crosshair size={32} /><p>Run monitoring once to capture your scene.</p><small>You can still use the full image as your region.</small></div>}
    <svg viewBox="0 0 1000 1000" preserveAspectRatio="none" aria-label="Selected monitoring region"><rect x={roi[0]*1000} y={roi[1]*1000} width={roi[2]*1000} height={roi[3]*1000} /></svg>
  </div>
}

export default function App() {
  const [view, setView] = useState<'monitor' | 'history' | 'settings'>('monitor')
  const [status, setStatus] = useState(initial)
  const [source, setSource] = useState<Source | null>(null)
  const [events, setEvents] = useState<Page>(empty)
  const [filter, setFilter] = useState('')
  const [page, setPage] = useState(1)
  const [error, setError] = useState('')
  const [connection, setConnection] = useState(true)
  const [busy, setBusy] = useState(false)
  const [detail, setDetail] = useState<Occurrence | null>(null)
  const [note, setNote] = useState('')
  const [decision, setDecision] = useState('person_present')
  const [notice, setNotice] = useState('')
  const [dbOk, setDbOk] = useState(false)
  const [modelOk, setModelOk] = useState(false)
  const active = ['starting', 'running', 'stopping'].includes(status.state)

  const loadEvents = useCallback(async () => {
    const result = await api<Page>(`/occurrences?page=${page}${filter ? `&classification=${filter}` : ''}`)
    setEvents(result)
  }, [page, filter])

  useEffect(() => {
    let mounted = true
    const poll = async () => {
      try { const value = await api<MonitorStatus>('/monitor/status'); if (mounted) { setStatus(value); setConnection(true) } }
      catch { if (mounted) setConnection(false) }
    }
    void poll(); const interval = setInterval(() => void poll(), 1000)
    return () => { mounted = false; clearInterval(interval) }
  }, [])

  useEffect(() => {
    const load = async () => {
      try { await loadEvents() } catch (e) { setError((e as Error).message) }
      try {
        const health = await fetch('/health/ready').then(r => r.json())
        setDbOk(health.database); setModelOk(health.model_available)
      } catch { setDbOk(false) }
    }
    void load(); const timer = setInterval(() => void load(), 5000)
    return () => clearInterval(timer)
  }, [loadEvents])

  useEffect(() => { api<Source>('/source').then(setSource).catch(e => setError(e.message)) }, [])
  useEffect(() => { if (!notice) return; const timer = setTimeout(() => setNotice(''), 4000); return () => clearTimeout(timer) }, [notice])

  async function action(operation: () => Promise<unknown>, success?: string) {
    setBusy(true); setError('')
    try { await operation(); if (success) setNotice(success) }
    catch (e) { setError((e as Error).message) }
    finally { setBusy(false) }
  }
  const control = (command: string) => action(async () => { setStatus(await api<MonitorStatus>(`/monitor/${command}`, 'POST')) })
  const open = (id: string) => action(async () => { setDetail(await api<Occurrence>(`/occurrences/${id}`)); setNote(''); setDecision('person_present') })
  async function saveReview() {
    if (!detail) return
    await action(async () => {
      await api(`/occurrences/${detail.id}/reviews`, 'POST', { decision, note })
      setDetail(await api<Occurrence>(`/occurrences/${detail.id}`)); setNote(''); await loadEvents()
    }, 'Review saved. Automatic classification preserved.')
  }

  const list = (compact = false) => <div className="event-list">
    {events.items.length === 0 ? <div className="empty"><History size={30} /><h3>Your history starts here</h3><p>Start a session. Motion or human presence in your region will create an occurrence.</p></div> : events.items.slice(0, compact ? 4 : 20).map(event => <button className="event-row" key={event.id} onClick={() => void open(event.id)}>
      <div className={`event-thumb ${event.classification}`}>{event.evidence_id ? <img src={`/api/evidence/${event.evidence_id}`} alt="Occurrence evidence" /> : <Scan size={22} />}</div>
      <div className="event-copy"><strong>{event.classification === 'person_detected' ? 'Human presence in region' : event.classification === 'no_person_detected' ? 'Motion without a detected person' : 'Analysis needs attention'}</strong><span>{date(event.started_at)} <i>·</i> {event.status}</span></div>
      <div className="event-meta"><Badge value={event.classification} /><small>{event.review ? 'Reviewed' : 'Awaiting review'}</small></div><ChevronRight size={17} />
    </button>)}
  </div>

  return <div className="app-shell">
    <aside className="sidebar">
      <a className="brand" href="#" onClick={() => { setFilter(''); setPage(1); setView('monitor') }}><span className="brand-symbol"><Scan size={23} /></span><span>SITEWATCH<span className="brand-ai">AI</span><small>VIDEO INTELLIGENCE</small></span></a>
      <div className="workspace-label">WORKSPACE <span>01</span></div>
      <nav aria-label="Main navigation">
        <button className={view === 'monitor' ? 'selected' : ''} onClick={() => { setFilter(''); setPage(1); setView('monitor') }}><LayoutDashboard size={18} />Overview<span className="nav-dot" /></button>
        <button className={view === 'history' ? 'selected' : ''} onClick={() => setView('history')}><History size={18} />Occurrences<span className="nav-count">{events.total}</span></button>
        <button className={view === 'settings' ? 'selected' : ''} onClick={() => setView('settings')}><Settings2 size={18} />Configuration</button>
      </nav>
      <div className="sidebar-note"><ShieldCheck size={20} /><strong>Your footage stays here.</strong><p>Inference, evidence, and history run locally on this computer.</p><span>LOCAL-FIRST BY DESIGN <ArrowDownLeft size={13} /></span></div>
      <a className="api-link" href="/docs" target="_blank" rel="noreferrer"><FileText size={17} />API documentation<ExternalLink size={13} /></a>
      <div className="profile"><div className="avatar">SW</div><div><strong>Local workspace</strong><small>Portfolio edition · v0.1</small></div><span className="tiny-dot" /></div>
    </aside>

    <main>
      <header className="topbar"><div className="breadcrumb">Workspace <ChevronRight size={13} /><span>{view === 'monitor' ? 'Overview' : view === 'history' ? 'Occurrences' : 'Configuration'}</span></div><div className="topbar-right"><span className="local-pill"><span className={`tiny-dot ${connection && dbOk ? '' : 'muted'}`} />{connection ? 'Local environment' : 'Backend offline'}</span><span className="edition">LEARNING LAB</span></div></header>
      <div className="content">
        <div className="page-heading"><div><div className="eyebrow">SEE THE SIGNAL. UNDERSTAND THE EVENT.</div><h1>{view === 'monitor' ? 'A clearer view of your site.' : view === 'history' ? 'Every event, in context.' : 'Define what matters.'}</h1><p>{view === 'monitor' ? 'Separate movement from human presence. Keep the evidence that matters.' : view === 'history' ? 'Explore the evidence and add a human review to the automatic result.' : 'Configure the camera, region, and detection thresholds for your next session.'}</p></div>{view !== 'settings' && <button className={`button ${active ? 'secondary' : 'primary'}`} disabled={busy || !connection || status.state === 'stopping'} onClick={() => void control(active ? 'stop' : 'start')}>{busy || status.state === 'starting' ? <LoaderCircle size={16} className="spin" /> : active ? <Pause size={16} /> : <Play size={16} />}{active ? 'Stop monitoring' : 'Start monitoring'}</button>}</div>
        {(!connection || error || status.error) && <div className="alert" role="alert"><Activity size={18} /><span>{!connection ? 'Cannot reach the backend. Start the Python service and retry.' : error || status.error}</span>{error && <button aria-label="Dismiss message" onClick={() => setError('')}><X size={16} /></button>}</div>}
        {notice && <div className="toast" role="status"><Check size={16} />{notice}</div>}

        {view === 'monitor' && <>
          <section className="stats" aria-label="Live monitoring metrics">
            <div className="stat"><span className="stat-label">PEOPLE VISIBLE <Users size={17} /></span><div className="stat-value">{status.people.toString().padStart(2, '0')}<span className="stat-tag">LIVE COUNT</span></div><p>{status.people_in_region} inside the monitored region</p></div>
            <div className="stat"><span className="stat-label">MOTION SIGNAL <Activity size={17} /></span><div className={`stat-word ${status.motion ? 'accent' : ''}`}>{active ? status.warming_up ? 'Adapting' : status.motion ? 'Detected' : 'Quiet' : 'Standby'}<span className="signal-bars"><i /><i /><i /><i /></span></div><p>Independent of human presence</p></div>
            <div className="stat"><span className="stat-label">ANALYSIS SPEED <Radar size={17} /></span><div className="stat-value">{status.analysis_fps.toFixed(1)}<span className="unit">fps</span></div><p>{status.inference_ms.toFixed(0)} ms inference · {status.frame_age_ms.toFixed(0)} ms frame age</p></div>
            <div className="stat"><span className="stat-label">OCCURRENCES <History size={17} /></span><div className="stat-value">{events.total.toString().padStart(2, '0')}<ArrowRight size={21} /></div><p>{status.occurrence_id ? 'An occurrence is currently active' : 'Grouped events, ready for review'}</p></div>
          </section>
          <div className="monitor-layout"><section className="panel camera-panel"><div className="panel-heading"><div><Camera size={18} /><h2>{source?.name || 'Notebook webcam'}</h2></div><span className={`feed-status ${status.state === 'running' ? 'live' : ''}`}><Circle size={7} fill="currentColor" />{status.state === 'running' ? 'LIVE' : status.state.toUpperCase()}</span></div>
            <div className="camera-view">
              {status.processed_frames > 0 ? <><img className="live-feed" src="/api/monitor/stream" alt="Camera view annotated with people and monitored region" /><div className="feed-overlay"><span><span className="tiny-dot" />{active ? 'LOCAL ANALYSIS' : 'LAST CAPTURED FRAME'}</span><span>{status.people} PEOPLE</span></div></> : <div className="camera-empty"><div className="viewfinder"><Camera size={34} strokeWidth={1.2} /><span /><span /><span /><span /></div><h3>{status.state === 'starting' ? 'Preparing your session' : 'Ready when you are.'}</h3><p>{status.state === 'starting' ? 'Loading the detector and connecting to your camera.' : 'Start monitoring to see your camera and live detections.'}</p><span className="camera-empty-label">ONE CAMERA. EVERY SIGNAL IN CONTEXT.</span></div>}
              <span className="camera-corner"><Maximize size={16} /></span>
            </div><div className="camera-footer"><span><span className="legend-person" />Person detected</span><span><span className="legend-region" />Monitored region</span><span className="camera-footer-right">{status.processed_frames} frames analyzed</span></div></section>
            <aside className="right-column"><section className="panel session-panel"><div className="panel-heading"><div><Activity size={17} /><h2>Session health</h2></div></div><div className="health-row"><span>Video pipeline</span><strong><span className={`tiny-dot ${status.state === 'running' ? '' : 'muted'}`} />{status.state === 'running' ? 'Running' : status.state === 'error' ? 'Interrupted' : active ? 'Starting' : 'Idle'}</strong></div><div className="health-row"><span>PostgreSQL</span><strong><span className={`tiny-dot ${dbOk ? '' : 'muted'}`} />{dbOk ? 'Connected' : 'Unavailable'}</strong></div><div className="health-row"><span>Detection model</span><strong><span className={`tiny-dot ${modelOk ? '' : 'muted'}`} />{modelOk ? 'Available' : 'Not downloaded'}</strong></div><div className="health-row"><span>Processing</span><strong>On this computer</strong></div><div className="session-foot"><ShieldCheck size={15} />Evidence is stored locally.</div></section>
            <section className="insight-card"><div className="insight-label"><Eye size={19} />A SIGNAL ISN’T A VERDICT</div><h3>Movement doesn’t<br />always mean a person.</h3><p>Motion and AI run independently. A person standing still can still be detected. An uncertain analysis stays uncertain.</p><button onClick={() => setView('history')}>Review your occurrences <ArrowRight size={16} /></button></section></aside>
          </div>
          <section className="panel recent-panel"><div className="panel-heading"><div><History size={17} /><h2>Recent occurrences</h2><span className="subtle-count">{events.total}</span></div><button className="text-button" onClick={() => { setFilter(''); setPage(1); setView('history') }}>View history <ArrowRight size={15} /></button></div>{list(true)}</section>
        </>}

        {view === 'history' && <section className="panel"><div className="panel-heading history-heading"><div><History size={18} /><h2>Occurrence log</h2><span className="subtle-count">{events.total}</span></div><label className="filter-label">Result<select value={filter} onChange={e => { setFilter(e.target.value); setPage(1) }}><option value="">All results</option><option value="person_detected">Person detected</option><option value="no_person_detected">No person detected</option><option value="inconclusive">Inconclusive</option></select></label></div>{list()}<div className="pagination"><span>Page {page} · {events.total} occurrences</span><div><button aria-label="Previous page" disabled={page === 1} onClick={() => setPage(p => p-1)}><ChevronLeft size={16} /></button><button aria-label="Next page" disabled={page*20 >= events.total} onClick={() => setPage(p => p+1)}><ChevronRight size={16} /></button></div></div></section>}

        {view === 'settings' && <div className="settings-grid"><section className="panel"><div className="panel-heading"><div><Crosshair size={18} /><h2>Monitored region</h2></div><button className="text-button" disabled={!source || active} onClick={() => source && setSource({ ...source, roi: [0, 0, 1, 1] })}>Reset to full frame</button></div>{source && <RegionEditor roi={source.roi} hasFrame={status.processed_frames > 0} change={roi => !active && setSource({ ...source, roi })} />}<p className="field-help">Stop monitoring, then drag to draw a rectangle. A person’s bottom-center point must be inside this area.</p></section><section className="panel settings-form"><div className="panel-heading"><div><Settings2 size={18} /><h2>Detection settings</h2></div></div>{source ? <form onSubmit={e => { e.preventDefault(); void action(async () => { setSource(await api<Source>('/source', 'PATCH', source)) }, 'Configuration saved for the next session.') }}><fieldset disabled={active || busy}><label>Source name<input value={source.name} maxLength={120} required onChange={e => setSource({ ...source, name: e.target.value })} /></label><label>Camera index<input type="number" min="0" max="20" value={source.camera_index} onChange={e => setSource({ ...source, camera_index: Number(e.target.value) })} /></label><label>Minimum confidence <span>{(source.confidence*100).toFixed(0)}%</span><input type="range" min="0.05" max="1" step="0.05" value={source.confidence} onChange={e => setSource({ ...source, confidence: Number(e.target.value) })} /></label><p className="field-help">A model score, not a guaranteed probability of correctness.</p><label>Motion threshold <span>{(source.motion_threshold*100).toFixed(1)}% of region</span><input type="range" min="0.001" max="0.2" step="0.001" value={source.motion_threshold} onChange={e => setSource({ ...source, motion_threshold: Number(e.target.value) })} /></label><button className="button primary" type="submit"><Check size={16} />Save configuration</button></fieldset>{active && <p className="field-help">Stop monitoring to edit configuration.</p>}</form> : <div className="empty"><Database size={28} /><p>Connect PostgreSQL and run migrations to configure your source.</p><code>sitewatch migrate</code></div>}</section></div>}

        <footer className="page-footer"><span><Scan size={14} />SITEWATCH AI <i>/</i> LOCAL VIDEO ANALYTICS</span><span>Built to observe. Designed to explain.</span></footer>
      </div>
    </main>

    {detail && <div className="modal-backdrop" onClick={e => { if (e.target === e.currentTarget) setDetail(null) }}><section className="modal" role="dialog" aria-modal="true" aria-labelledby="detail-title" onKeyDown={e => { if (e.key === 'Escape') setDetail(null) }}><div className="modal-heading"><div><div className="eyebrow">OCCURRENCE DETAILS</div><h2 id="detail-title">Review the evidence.</h2></div><button className="icon-button" aria-label="Close details" onClick={() => setDetail(null)} autoFocus><X size={22} /></button></div><div className="detail-summary"><Badge value={detail.classification} /><span><Clock3 size={14} />{date(detail.started_at)}</span><span>{detail.status}</span></div><div className="detail-images">{detail.evidence?.map(e => <figure key={e.id}><img src={`/api/evidence/${e.id}`} alt={`${e.kind} occurrence evidence`} /><figcaption>{e.kind} · {date(e.captured_at)}</figcaption></figure>)}</div><div className="detail-metrics"><div><strong>{detail.peak_people}</strong><span>Peak people in region</span></div><div><strong>{detail.summary.valid_samples || 0}</strong><span>Successful analyses</span></div><div><strong>{detail.summary.max_analysis_gap_seconds?.toFixed(2) || '0'}s</strong><span>Largest analysis gap</span></div></div><h3>Human review</h3><p className="field-help">Record what you can verify in the evidence. Your review does not overwrite the automatic result.</p><label className="review-decision">Decision<select disabled={detail.status === 'active'} value={decision} onChange={e => setDecision(e.target.value)}><option value="person_present">Person present</option><option value="no_person">No person visible</option><option value="uncertain">Uncertain</option></select></label><textarea aria-label="Review notes" value={note} onChange={e => setNote(e.target.value)} maxLength={2000} placeholder="Add context, limitations, or anything the detector missed…" disabled={detail.status === 'active'} /><button className="button primary" disabled={busy || detail.status === 'active'} onClick={() => void saveReview()}><Check size={16} />{detail.status === 'active' ? 'Wait for occurrence to close' : 'Save review'}</button>{detail.reviews?.map(review => <div className="review-entry" key={review.id}><strong>{labels[review.decision]}</strong><span>{date(review.created_at)}</span><p>{review.note || 'No additional notes.'}</p></div>)}<details><summary>Analysis observations ({detail.observations?.length || 0} most recent)</summary><div className="observations">{detail.observations?.map(o => <div key={o.id}><span>{date(o.captured_at)}</span><span>{o.person_count} people</span><span>{(o.motion_score*100).toFixed(1)}% motion</span></div>)}</div></details><small className="event-id">ID {detail.id}</small></section></div>}
  </div>
}
