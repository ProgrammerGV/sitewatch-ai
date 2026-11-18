"""Pure rules: no OpenCV, database, web server, or model dependency."""

from dataclasses import dataclass, field
from typing import Literal

Classification = Literal["person_detected", "no_person_detected", "inconclusive"]


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
        self.max_gap = max(self.max_gap, now - (self.last_sample or self.started))
        self.last_sample = now

    def classify(self, interrupted: bool = False) -> Classification:
        if self.person_confirmed:
            return "person_detected"
        if interrupted or self.failed or self.valid_samples < 3 or self.max_gap > 2:
            return "inconclusive"
        return "no_person_detected"


@dataclass
class EventRules:
    confirmation_window: float = 2
    idle_seconds: float = 5
    state: EventState | None = None
    hits: list[float] = field(default_factory=list)
    motion_hits: list[float] = field(default_factory=list)

    def step(self, now: float, motion: bool, people: int) -> tuple[bool, bool]:
        """Return (opened, closed). Presence is independent of the motion signal."""
        self.hits = [t for t in self.hits if now - t <= self.confirmation_window]
        self.motion_hits = [t for t in self.motion_hits if now - t <= self.confirmation_window]
        if people:
            self.hits.append(now)
        if motion:
            self.motion_hits.append(now)
        confirmed = people > 0 and len(self.hits) >= 2
        motion_confirmed = motion and len(self.motion_hits) >= 2
        opened = False
        if self.state is None and (confirmed or motion_confirmed):
            self.state = EventState(now, now)
            opened = True
        if self.state is None:
            return False, False
        self.state.sample(now, people, confirmed)
        # Once confirmed, every positive observation maintains presence, even while still.
        if motion_confirmed or (people and self.state.person_confirmed):
            self.state.last_activity = now
        closed = now - self.state.last_activity >= self.idle_seconds
        return opened, closed

    def reset(self) -> None:
        self.state = None
        self.hits.clear()
        self.motion_hits.clear()
