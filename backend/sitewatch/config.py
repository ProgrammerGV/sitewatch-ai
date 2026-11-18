from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(ROOT / ".env"), extra="ignore")
    database_url: str = "postgresql+psycopg://sitewatch:change-me@127.0.0.1:5432/sitewatch"
    data_dir: Path = ROOT / "data"
    model_name: str = "yolo26n.pt"
    model_path: Path = ROOT / "data/models/yolo26n.pt"
    model_device: str = "cpu"
    camera_index: int = Field(0, ge=0)
    inference_fps: float = Field(3, ge=0.5, le=30)
    confidence_threshold: float = Field(0.5, ge=0.05, le=1)
    confirmation_window_seconds: float = Field(2, gt=0)
    event_idle_seconds: float = Field(5, gt=0)
    motion_threshold: float = Field(0.01, gt=0, le=1)
    motion_warmup_seconds: float = Field(5, ge=0)
    max_evidence_mb: int = Field(2048, ge=1)

    def absolute(self, path: Path) -> Path:
        return path if path.is_absolute() else ROOT / path


@lru_cache
def get_settings() -> Settings:
    return Settings()
