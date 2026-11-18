from typing import Literal

from pydantic import BaseModel, Field, model_validator


class SourceUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    camera_index: int = Field(ge=0, le=20)
    roi: tuple[float, float, float, float]
    confidence: float = Field(ge=0.05, le=1)
    motion_threshold: float = Field(gt=0, le=1)

    @model_validator(mode="after")
    def valid_region(self):
        x, y, width, height = self.roi
        if not (
            0 <= x < 1
            and 0 <= y < 1
            and 0.01 <= width <= 1
            and 0.01 <= height <= 1
            and x + width <= 1.000001
            and y + height <= 1.000001
        ):
            raise ValueError("Region must be a non-empty rectangle inside the normalized image.")
        return self


class ReviewInput(BaseModel):
    decision: Literal["person_present", "no_person", "uncertain"]
    note: str = Field(default="", max_length=2000)
