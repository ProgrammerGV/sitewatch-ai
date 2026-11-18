# Learning guide

Work through these experiments before adding features. Keep a short log of the change, expected result, observed result, and any trade-off.

## 1. Follow one image

Read `LatestFrameCapture`, `YoloDetector.detect`, `Detection.in_region`, and `EventRules.step`, in that order. Trace how image pixels become boxes, application data, and an occurrence.

Experiment: move your hand or an object without entering the scene. Then enter and stand still. Compare the motion signal with presence detection. A moving object may still be incorrectly classified; record what actually happens.

## 2. Understand confirmation and time

Read the pure-rule tests before changing a threshold. Run only those tests while experimenting.

Experiment: change the confirmation window and idle timeout. Observe how short detection gaps affect event grouping. Explain why a frame count alone cannot represent a stable duration when inference speed changes.

## 3. Understand the region

Draw a small rectangle. Test a person inside, outside, and crossing its boundary. The chosen rule uses the bottom-center of a box, which is an approximation of where someone stands; it has limitations with occlusion, close-up views, and camera perspective.

Explain why normalized coordinates survive changes in image resolution and why the browser must preserve the image's aspect ratio.

## 4. Explore the database

Inspect a session and its configuration snapshot. Join its occurrences to observations and evidence. Add two manual reviews and verify that both remain, while the automatic result is unchanged.

Explain the difference between a frame, a detection, an observation row, an occurrence, a review, and an identity. Document why the project has no identity table.

## 5. Introduce failures

Stop PostgreSQL in a disposable development environment during monitoring, or disconnect the webcam. Verify the visible error. Restore the dependency and restart the application. Check the previous session's lifecycle and its preserved positive evidence.

Never experiment against databases shared with other applications. Integration tests require their own `_test` database.

## 6. Measure instead of guessing

Record short scenarios with consent: empty scene, moving object, person entering, stationary person, person outside the region, partial occlusion, and difficult lighting. Label the expected event-level result before reviewing model output.

Track missed person events, false person events, inconclusive events, time to confirmation, inference time, frame age, and processing speed. Report the sample size. Do not treat a single successful demonstration as an accuracy benchmark.

## 7. Explain the architecture

Prepare a three-minute demo: configure a region, run a scene, inspect an occurrence, add a review, and explain one failure mode. Present one trade-off you measured and one limitation you have not solved.

For a portfolio video, use staged footage with permission and keep private workplace images and camera credentials out of the recording.
