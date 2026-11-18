"""Validated runtime state; serialized field names remain compatible with the API."""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class MonitorPhase(StrEnum):
    IDLE = "idle"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    ERROR = "error"


class MonitorStatus(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    state: MonitorPhase = MonitorPhase.IDLE
    error: str | None = None
    people: int = Field(0, ge=0)
    people_in_region: int = Field(0, ge=0)
    motion: bool = False
    motion_score: float = 0
    warming_up: bool = False
    inference_ms: float = 0
    frame_age_ms: float = 0
    processed_frames: int = Field(0, ge=0)
    analysis_fps: float = 0
    session_id: str | None = None
    occurrence_id: str | None = None
    person_confirmed: bool = False

    def with_changes(self, **changes: object) -> "MonitorStatus":
        return MonitorStatus.model_validate({**self.model_dump(), **changes})
