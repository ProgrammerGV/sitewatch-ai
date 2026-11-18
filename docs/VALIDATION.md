# Validation record

Initial local validation: **November 18, 2026**, Windows notebook, approximately 16 GB RAM, Python 3.12, CPU inference, PostgreSQL 16.

## Automated checks

- **21 tests passed** with the isolated PostgreSQL test database enabled.
- Backend static checks passed after formatting and import cleanup.
- TypeScript checking and the production frontend build passed.
- The migration was applied to fresh application and test databases.
- GitHub Actions also passed both jobs on Ubuntu: backend with PostgreSQL 16 and the frontend build/runtime dependency audit.
- The full npm development dependency audit has the unresolved glob-matching advisory described in [SECURITY.md](../SECURITY.md).

Tests use controlled detections for deterministic rule and failure checks. They do not establish the accuracy of the real detector. Integration tests run in their own randomly named PostgreSQL schemas and remove those schemas afterward.

## Real-model replay

A private 32-second video was constructed for repeatable pipeline verification: an empty scene, a moving white rectangle, a quiet interval, an official Ultralytics example image containing people held stationary, and a final quiet interval. The input is an artificial test, not representative site footage.

The real YOLO26n model processed **91 frames** at an observed average **2.66 analyses/second**. The last reported inference time was **63 ms**, with a **188 ms** frame age. These are observations from one run, not latency percentiles or a general performance guarantee.

The database recorded:

| Scenario | Automatic result | Lifecycle | Peak people | Successful analyses |
| --- | --- | --- | --- | --- |
| Moving rectangle | No person detected | Closed | 0 | 27 |
| Stationary image containing people | Person detected | Closed | 4 | 40 |

The maximum recorded analysis gaps were approximately 0.41 and 0.39 seconds. This verifies that presence does not require continuing movement and that the pipeline can close a motion-only occurrence without calling it a proven false alarm.

The example image, replay video and generated evidence are not published in this repository. Source for the private replay image: the official `ultralytics/ultralytics` example asset `ultralytics/assets/bus.jpg`.

## Webcam and browser smoke test

- Started capture through the actual dashboard and confirmed live inference and region counts.
- Observed roughly 2–3 analyses/second and a displayed inference time around 78 ms during a short sample.
- Stopped capture and inspected the persisted occurrence and its evidence metadata.
- Saved an explicit uncertain manual review, preserving automatic classification and review history.
- Saved source configuration through the form.
- Checked the desktop layout at 1440 px and a narrow layout at 390 px; the narrow view had no horizontal overflow.

Webcam imagery and runtime evidence remain local and ignored by Git. Repository screenshots show only the interface without personal footage. The manual smoke-test review does not assert that detector accuracy was independently verified.

## What remains unvalidated

- Recall, precision and false-alarm reduction on representative telecom-site footage.
- Night/infrared images, weather, distant people, severe occlusion and camera vibration.
- Long-running stability, disk growth, thermal throttling and recovery under repeated outages.
- Actual Hikvision/other camera models, firmware, RTSP transport and remote connectivity.
- Commercial cloud costs, multi-tenant security and end-to-end notification delivery.

A staged local demonstration supports this learning project; it does not establish commercial monitoring readiness.

## Clean Code refactor validation — November 18, 2026

- 31 backend tests passed with PostgreSQL integration enabled.
- 4 native Node API-client tests passed, including cancellation and non-JSON proxy errors.
- TypeScript checking and the separate production build passed.
- Alembic reported no schema changes.
- Browser verification used port 8001, a disposable PostgreSQL schema and a controlled inconclusive occurrence. Configuration persistence and review history passed, without opening the webcam or modifying the user's live history.

The original port-8000 process and frontend build remained intact during implementation so local testing could continue.
