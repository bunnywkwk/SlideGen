from pathlib import Path
from typing import Callable

from .constants import BACKEND_OUTPUT_DIR, LEGACY_LYRICS_DIR, resolve_project_path
from .lyrics_domain import (
    build_song_chunks,
    parse_song_text,
    resolve_template,
    song_to_draft_text,
    unique_output_path,
    validate_song_text,
)
from .presentation_legacy import create_lyrics_presentation as create_lyrics_presentation_legacy
from .presentation_portable import create_lyrics_presentation as create_lyrics_presentation_portable
from .schemas import (
    LyricsChunkPreview,
    LyricsGenerateRequest,
    LyricsPreviewResponse,
    LyricsSongPreview,
)
from .settings import load_settings

ProgressCallback = Callable[[int, str], None] | None


def _report(progress_callback: ProgressCallback, progress: int, message: str) -> None:
    if progress_callback is not None:
        progress_callback(progress, message)


def get_default_lyrics_template() -> Path:
    return resolve_template(None, LEGACY_LYRICS_DIR / "samples-ppt")


def resolve_lyrics_template(raw_template_path: str | None) -> Path:
    if raw_template_path:
        template_path = resolve_project_path(raw_template_path)
        if not template_path.exists():
            raise FileNotFoundError(f"Lyrics template not found: {template_path}")
        return template_path
    return get_default_lyrics_template()


def _build_song_objects(
    request: LyricsGenerateRequest,
    progress_callback: ProgressCallback = None,
    start_progress: int = 10,
    end_progress: int = 35,
):
    songs = []
    total_songs = max(len(request.songs), 1)

    for index, song_input in enumerate(request.songs, start=1):
        songs.append(
            parse_song_text(
                song_input.lyrics,
                source_name=f"Song {index}",
                title_hint=song_input.title,
            )
        )
        progress = start_progress + ((end_progress - start_progress) * index / total_songs)
        _report(progress_callback, progress, f"Parsing songs ({index}/{total_songs})...")

    return songs


def build_lyrics_preview(request: LyricsGenerateRequest, progress_callback: ProgressCallback = None) -> LyricsPreviewResponse:
    settings = load_settings()
    if request.template_path and not settings.enable_legacy_templates:
        raise ValueError("Custom template paths are disabled on this server.")
    _report(progress_callback, 8, "Preparing lyrics preview...")
    songs = _build_song_objects(request, progress_callback=progress_callback, start_progress=12, end_progress=38)
    preview_songs: list[LyricsSongPreview] = []
    total_songs = max(len(songs), 1)

    for index, (song_input, song) in enumerate(zip(request.songs, songs), start=1):
        warnings = validate_song_text(song_input.lyrics, song_input.title)
        chunks = build_song_chunks(song, include_verse_labels=request.include_verse_labels)
        preview_songs.append(
            LyricsSongPreview(
                title=song.title,
                warnings=warnings,
                slide_count=1 + len(chunks),
                draft_text=song_to_draft_text(song),
                chunks=[
                    LyricsChunkPreview(
                        section_name=chunk.section_name,
                        section_label=chunk.section_label,
                        lines=list(chunk.lines),
                    )
                    for chunk in chunks
                ],
            )
        )
        progress = 40 + ((88 - 40) * index / total_songs)
        _report(progress_callback, progress, f"Building preview ({index}/{total_songs})...")

    total_slide_count = sum(song.slide_count for song in preview_songs)
    response = LyricsPreviewResponse(
        presentation_mode="template-based" if request.template_path and settings.enable_legacy_templates else "portable",
        total_slide_count=total_slide_count,
        songs=preview_songs,
    )
    _report(progress_callback, 100, "Lyrics preview ready.")
    return response


def generate_lyrics_ppt(request: LyricsGenerateRequest, progress_callback: ProgressCallback = None) -> Path:
    settings = load_settings()
    if request.template_path and not settings.enable_legacy_templates:
        raise ValueError("Custom template paths are disabled on this server.")
    _report(progress_callback, 8, "Preparing lyrics export...")
    songs = _build_song_objects(request, progress_callback=progress_callback, start_progress=12, end_progress=32)
    BACKEND_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = unique_output_path(BACKEND_OUTPUT_DIR, 1)
    _report(progress_callback, 42, "Preparing PowerPoint layout...")

    if request.template_path and settings.enable_legacy_templates:
        template_path = resolve_lyrics_template(request.template_path)
        _report(progress_callback, 76, "Rendering PowerPoint slides...")
        create_lyrics_presentation_legacy(
            template_path=template_path,
            output_path=output_path,
            songs=songs,
            include_welcome_slide=request.include_welcome_slide,
            include_verse_labels=request.include_verse_labels,
        )
    else:
        _report(progress_callback, 76, "Rendering PowerPoint slides...")
        create_lyrics_presentation_portable(
            output_path=output_path,
            songs=songs,
            include_welcome_slide=request.include_welcome_slide,
            include_verse_labels=request.include_verse_labels,
            build_song_chunks=build_song_chunks,
        )
    _report(progress_callback, 100, "Lyrics PowerPoint ready.")
    return output_path
