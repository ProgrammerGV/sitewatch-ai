# Clean Code refactoring walkthrough

The first implementation established a working end-to-end flow. This pass separates the responsibilities that made changes and tests harder, while keeping HTTP paths, database columns, default detection policy and visual layout compatible.

## Backend

Follow this sequence:

1. **`capture.py`:** `LatestFrameCapture` owns the camera thread and publishes a named `FramePacket`. End-of-video is an explicit completion flag, separate from an error message.
2. **`pipeline.py`:** `FrameAnalyzer` receives plain `FrameSettings` and a detector interface. It returns a `FrameAnalysis` with boxes, motion and timing; it does not read the UI state or use a database model.
3. **`domain.py`:** `EventRules` decides whether an occurrence opens/closes, returning a named `EventTransition`. It depends on neither camera hardware nor persistence.
4. **`pipeline.py`:** `OccurrenceRecorder` applies those transitions through a narrow persistence interface. It owns evidence selection and observation cadence. The first human-confirmation transition is derived directly from the rule state.
5. **`storage.py` and `evidence.py`:** PostgreSQL writes and filesystem/JPEG operations have separate owners. Quota and encoding failures can be tested without a database.
6. **`monitor.py`:** `Monitor` manages start/stop, resource cleanup, and publication of validated `MonitorStatus` snapshots. It composes the preceding objects.
7. **`app.py` and `routes/`:** the application factory composes lifecycle/middleware and route groups. Route paths and request bodies remain compatible with the original dashboard.

`policy.py` gives separate names to frame freshness, negative-analysis coverage, sample cadence, and capture timeouts. Two defaults can have the same numerical value while representing different concepts.

## Frontend

`App.tsx` composes pages rather than owning fetching and hundreds of lines of markup.

- **Pages:** `MonitorPage`, `HistoryPage`, `SettingsPage` receive data and callbacks.
- **Components:** live metrics, camera feed, health, occurrence list/dialog and region editor each own their presentation.
- **Hooks:** `useMonitor`, `useHealth`, and `useOccurrenceHistory` own data updates. Polling cancels outstanding requests on cleanup and avoids overlapping scheduled requests.
- **Application actions:** `useDashboard` coordinates navigation, configuration and reviews. Request generations prevent older detail/history responses from replacing newer selections.
- **Contracts:** `types.ts` contains state/classification/decision unions; `api.ts` handles HTTP; `presentation.ts` handles labels and timestamps.

The composition file went from 941 to 72 lines, and the monitor worker entry point went from 144 to 22. These measurements show narrower orchestration; responsibility, behavior and readability remain the criteria for assessing the result.

## Verification

The local suite now contains 31 backend tests and 4 API-client tests. New coverage checks invalid runtime states, representative evidence files, confirmation between observation intervals, stale/slow frames, finite-video completion and cleanup failures. A separate browser instance and throwaway PostgreSQL schema verify configuration and review flows without altering the live workspace.

No database migration is required for this pass. Existing history and evidence remain usable. The running local application is updated only while monitoring is idle; an active test session can keep using its loaded version until the next launch.

## Next learning exercise

Open an existing rule test, trace its transition into `OccurrenceRecorder`, then explain which module would change if evidence storage moved to object storage. Implement a new behavior only after identifying its owner and adding a meaningful scenario test.
