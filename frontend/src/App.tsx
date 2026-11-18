import { DashboardLayout } from './components/DashboardLayout'
import { OccurrenceDialog } from './components/OccurrenceDialog'
import { HistoryPage } from './pages/HistoryPage'
import { MonitorPage } from './pages/MonitorPage'
import { SettingsPage } from './pages/SettingsPage'
import { useDashboard } from './hooks/useDashboard'

export default function App() {
  const dashboard = useDashboard()
  const { status, source, events, view, active, feedback } = dashboard
  return (
    <DashboardLayout
      view={view}
      status={status}
      active={active}
      eventCount={events.total}
      connection={dashboard.connected}
      dbOk={dashboard.dbOk}
      busy={feedback.busy}
      error={feedback.error}
      notice={feedback.notice}
      onNavigate={dashboard.navigate}
      onControl={dashboard.control}
      onDismissError={feedback.dismissError}
    >
      {view === 'monitor' && (
        <MonitorPage
          status={status}
          source={source}
          active={active}
          dbOk={dashboard.dbOk}
          modelOk={dashboard.modelOk}
          events={events}
          onViewHistory={() => dashboard.navigate('history')}
          onOpenOccurrence={dashboard.openOccurrence}
        />
      )}
      {view === 'history' && (
        <HistoryPage
          events={events}
          filter={dashboard.filter}
          page={dashboard.page}
          onFilterChange={dashboard.setFilter}
          onPageChange={dashboard.setPage}
          onOpenOccurrence={dashboard.openOccurrence}
        />
      )}
      {view === 'settings' && (
        <SettingsPage
          source={source}
          onSourceChange={dashboard.setSource}
          onSave={dashboard.saveSource}
          active={active}
          busy={feedback.busy}
          hasFrame={status.processed_frames > 0}
        />
      )}
      {dashboard.detail && (
        <OccurrenceDialog
          detail={dashboard.detail}
          busy={feedback.busy}
          note={dashboard.note}
          decision={dashboard.decision}
          onClose={dashboard.closeOccurrence}
          onNoteChange={dashboard.setNote}
          onDecisionChange={dashboard.setDecision}
          onSave={dashboard.saveReview}
        />
      )}
    </DashboardLayout>
  )
}
