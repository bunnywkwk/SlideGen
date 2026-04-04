from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator
from .settings import load_settings


class SongInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    title: str = Field(..., min_length=1, max_length=120)
    lyrics: str = Field(..., min_length=1)


class LyricsGenerateRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    job_type: Literal["lyrics"]
    songs: list[SongInput] = Field(..., min_length=1, max_length=8)
    template_path: str | None = None
    include_welcome_slide: bool = False
    include_verse_labels: bool = False


class VersesGenerateRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    job_type: Literal["verses"]
    book: str = Field(..., min_length=1)
    chapter: int = Field(..., ge=1)
    start_verse: int = Field(1, ge=1)
    end_verse: int | None = Field(None, ge=1)
    left_version: str = Field("NIV11", min_length=1)
    right_version: str = Field("APD", min_length=1)
    language_ranges: str | None = None
    api_key: str | None = None
    template_path: str | None = None
    background_image_path: str | None = None
    header_font_name: str | None = None
    verse_font_name: str | None = None
    header_font_color: str | None = None
    verse_font_color: str | None = None

    @model_validator(mode="after")
    def validate_range(self) -> "VersesGenerateRequest":
        if not self.language_ranges:
            self.language_ranges = load_settings().default_language_ranges
        if self.end_verse is not None and self.end_verse < self.start_verse:
            raise ValueError("End verse must be greater than or equal to start verse.")
        return self


GenerateRequest = Annotated[LyricsGenerateRequest | VersesGenerateRequest, Field(discriminator="job_type")]


class LyricsChunkPreview(BaseModel):
    section_name: str
    section_label: str | None = None
    lines: list[str]


class LyricsSongPreview(BaseModel):
    title: str
    warnings: list[str]
    slide_count: int
    draft_text: str
    chunks: list[LyricsChunkPreview]


class LyricsPreviewResponse(BaseModel):
    presentation_mode: str
    total_slide_count: int
    songs: list[LyricsSongPreview]


class VersePreviewItem(BaseModel):
    verse_number: int
    left_text: str
    right_text: str


class VersesPreviewResponse(BaseModel):
    presentation_mode: str
    book: str
    chapter: int
    left_version: str
    right_version: str
    verse_count: int
    verses: list[VersePreviewItem]


class GenerateResponse(BaseModel):
    job_type: Literal["lyrics", "verses"]
    message: str
    lyrics_preview: LyricsPreviewResponse | None = None
    verses_preview: VersesPreviewResponse | None = None


class JobAcceptedResponse(BaseModel):
    job_id: str
    job_type: Literal["lyrics", "verses"]
    operation: Literal["preview", "ppt"]
    status: Literal["queued", "running"]
    progress: int
    message: str


class JobStatusResponse(BaseModel):
    job_id: str
    job_type: Literal["lyrics", "verses"]
    operation: Literal["preview", "ppt"]
    status: Literal["queued", "running", "completed", "failed"]
    progress: int
    message: str
    result: GenerateResponse | None = None
    download_ready: bool = False
    download_url: str | None = None
    error: str | None = None


class AppInfo(BaseModel):
    name: str
    ppt_engine: str
    verse_lookup_ready: bool
    allow_public_api_keys: bool


class DefaultsResponse(BaseModel):
    left_version: str
    right_version: str
    lyrics_song_slots: int


class OptionsResponse(BaseModel):
    books: list[str]
    bible_versions: list[str]
    defaults: DefaultsResponse
    app: AppInfo
    output_directory: str
