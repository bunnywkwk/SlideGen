import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

from .constants import (
    BACKEND_OUTPUT_DIR,
    DEFAULT_LANGUAGE_RANGES,
    DEFAULT_LEFT_VERSION,
    DEFAULT_LYRICS_SONG_SLOTS,
    DEFAULT_RIGHT_VERSION,
    DEFAULT_VERSION_OPTIONS,
)

BACKEND_ENV_PATH = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(BACKEND_ENV_PATH)


@dataclass(frozen=True)
class Settings:
    app_name: str
    cors_origins: list[str]
    output_directory: str
    ppt_engine: str
    enable_legacy_templates: bool
    allow_public_api_keys: bool
    youversion_api_key: str | None
    default_left_version: str
    default_right_version: str
    default_language_ranges: str
    default_lyrics_song_slots: int
    version_options: list[str]
    max_upload_size_bytes: int
    weekly_ppt_limit: int


def load_settings() -> Settings:
    cors_origins_raw = os.getenv("SLIDEGEN_CORS_ORIGINS", "*")
    version_options_raw = os.getenv("SLIDEGEN_VERSION_OPTIONS")

    if version_options_raw:
        version_options = [item.strip() for item in version_options_raw.split(",") if item.strip()]
    else:
        version_options = list(DEFAULT_VERSION_OPTIONS)

    return Settings(
        app_name=os.getenv("SLIDEGEN_APP_NAME", "SlideGen API"),
        cors_origins=[item.strip() for item in cors_origins_raw.split(",") if item.strip()],
        output_directory=str(BACKEND_OUTPUT_DIR),
        ppt_engine=os.getenv("SLIDEGEN_PPT_ENGINE", "portable").strip().lower(),
        enable_legacy_templates=os.getenv("SLIDEGEN_ENABLE_LEGACY_TEMPLATES", "false").lower() == "true",
        allow_public_api_keys=os.getenv("SLIDEGEN_ALLOW_PUBLIC_API_KEYS", "false").lower() == "true",
        youversion_api_key=os.getenv("SLIDEGEN_YOUVERSION_API_KEY"),
        default_left_version=os.getenv("SLIDEGEN_DEFAULT_LEFT_VERSION", DEFAULT_LEFT_VERSION),
        default_right_version=os.getenv("SLIDEGEN_DEFAULT_RIGHT_VERSION", DEFAULT_RIGHT_VERSION),
        default_language_ranges=os.getenv("SLIDEGEN_DEFAULT_LANGUAGE_RANGES", DEFAULT_LANGUAGE_RANGES),
        default_lyrics_song_slots=int(os.getenv("SLIDEGEN_DEFAULT_LYRICS_SONG_SLOTS", DEFAULT_LYRICS_SONG_SLOTS)),
        version_options=version_options,
        max_upload_size_bytes=int(os.getenv("SLIDEGEN_MAX_UPLOAD_SIZE_BYTES", str(8 * 1024 * 1024))),
        weekly_ppt_limit=max(0, int(os.getenv("SLIDEGEN_WEEKLY_PPT_LIMIT", "2"))),
    )
