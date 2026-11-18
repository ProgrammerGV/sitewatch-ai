"""Pure rules: no OpenCV, database, web server, or model dependency."""

from dataclasses import dataclass, field
from typing import Literal, NamedTuple

from .policy import (
    MAX_NEGATIVE_ANALYSIS_GAP_SECONDS,
    MIN_CONFIRMATION_SAMPLES,
    MIN_NEGATIVE_ANALYSIS_SAMPLES,
)

Classification = Literal["person_detected", "no_person_detected", "inconclusive"]


class EventTransition(NamedTuple):
    opened: bool
    closed: bool


@dataclass(frozen=True)
class Detection:
    confidence: float
    bbox: tuple[float, float, float, float]  # normalized x1, y1, x2, y2

    def in_region(self, roi: tuple[float, float, float, float]) -> bool:
        x1, _, x2, y2 = self.bbox
        left, top, width, height = roi
        return left <= (x1 + x2) / 2 <= left + width and top <= y2 <= top + height


@dataclass
class EventState:
    started: float
    last_activity: float
    person_confirmed: bool = False
    peak_people: int = 0
    valid_samples: int = 0
    failed: bool = False
    max_gap: float = 0
    last_sample: float | None = None

    def sample(self, now: float, count: int, confirmed: bool) -> None:
        self.valid_samples += 1
        self.peak_people = max(self.peak_people, count)
        self.person_confirmed |= confirmed
        previous_sample = self.started if self.last_sample is None else self.last_sample
        self.max_gap = max(self.max_gap, now - previous_sample)
        self.last_sample = now

    def classify(self, interrupted: bool = False) -> Classification:
        if self.person_confirmed:
            return "person_detected"
        insufficient_coverage = (
            self.valid_samples < MIN_NEGATIVE_ANALYSIS_SAMPLES
            or self.max_gap > MAX_NEGATIVE_ANALYSIS_GAP_SECONDS
        )
        if interrupted or self.failed or insufficient_coverage:
            return "inconclusive"
        return "no_person_detected"


@dataclass
class EventRules:
    confirmation_window: float = 2
    idle_seconds: float = 5
    state: EventState | None = None
    hits: list[float] = field(default_factory=list)
    motion_hits: list[float] = field(default_factory=list)

    def step(self, now: float, motion: bool, people: int) -> EventTransition:
        """Return (opened, closed). Presence is independent of the motion signal."""
        self.hits = [t for t in self.hits if now - t <= self.confirmation_window]
        self.motion_hits = [t for t in self.motion_hits if now - t <= self.confirmation_window]
        if people:
            self.hits.append(now)
        if motion:
            self.motion_hits.append(now)
        confirmed = people > 0 and len(self.hits) >= MIN_CONFIRMATION_SAMPLES
        motion_confirmed = motion and len(self.motion_hits) >= MIN_CONFIRMATION_SAMPLES
        opened = False
        if self.state is None and (confirmed or motion_confirmed):
            self.state = EventState(now, now)
            opened = True
        if self.state is None:
            return EventTransition(opened=False, closed=False)
        self.state.sample(now, people, confirmed)
        # Once confirmed, every positive observation maintains presence, even while still.
        if motion_confirmed or (people and self.state.person_confirmed):
            self.state.last_activity = now
        closed = now - self.state.last_activity >= self.idle_seconds
        return EventTransition(opened=opened, closed=closed)

    def reset(self) -> None:
        self.state = None
        self.hits.clear()
        self.motion_hits.clear()
