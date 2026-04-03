from datetime import datetime
from pathlib import Path
from typing import Callable

from .constants import BACKEND_OUTPUT_DIR, LEGACY_VERSES_DIR, PROJECT_ROOT, resolve_project_path
from .bible_client import find_bible_id, find_book_usfm, get_verses
from .presentation_legacy import create_verses_presentation as create_verses_presentation_legacy
from .presentation_portable import create_verses_presentation as create_verses_presentation_portable
from .schemas import VersePreviewItem, VersesGenerateRequest, VersesPreviewResponse
from .settings import load_settings

ProgressCallback = Callable[[int, str], None] | None


def _report(progress_callback: ProgressCallback, progress: int, message: str) -> None:
    if progress_callback is not None:
        progress_callback(progress, message)


def get_default_verses_template() -> Path:
    candidates = [
        LEGACY_VERSES_DIR / "November-26-24.pptx",
        PROJECT_ROOT / "November-26-24.pptx",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise FileNotFoundError("Could not find the default verses PowerPoint template.")


def resolve_verses_template(raw_template_path: str | None) -> Path:
    if raw_template_path:
        template_path = resolve_project_path(raw_template_path)
        if not template_path.exists():
            raise FileNotFoundError(f"Verses template not found: {template_path}")
        return template_path
    return get_default_verses_template()


def resolve_background_image_path(raw_path: str | None) -> Path | None:
    if not raw_path:
        return None
    path = resolve_project_path(raw_path)
    if not path.exists():
        raise FileNotFoundError(f"Background image not found: {path}")
    return path


def resolve_api_key(request: VersesGenerateRequest) -> str:
    settings = load_settings()
    if request.api_key:
        if settings.allow_public_api_keys:
            return request.api_key
        raise ValueError("This server is not configured to accept public API keys.")
    if settings.youversion_api_key:
        return settings.youversion_api_key
    raise ValueError("Verse lookup is not configured on this server yet.")


def _load_verses(request: VersesGenerateRequest, progress_callback: ProgressCallback = None):
    _report(progress_callback, 10, "Checking verse lookup access...")
    api_key = resolve_api_key(request)
    _report(progress_callback, 22, f"Finding {request.left_version} version...")
    left_id = find_bible_id(api_key, request.left_version, request.language_ranges)
    _report(progress_callback, 34, f"Finding {request.right_version} version...")
    right_id = find_bible_id(api_key, request.right_version, request.language_ranges)

    _report(progress_callback, 46, "Resolving book names...")
    left_book = find_book_usfm(api_key, left_id, request.book)
    _report(progress_callback, 56, "Resolving comparison book...")
    right_book = find_book_usfm(api_key, right_id, request.book)

    _report(progress_callback, 68, f"Fetching {request.left_version} verses...")
    left_verses = get_verses(api_key, left_id, left_book, request.chapter)
    _report(progress_callback, 80, f"Fetching {request.right_version} verses...")
    right_verses = get_verses(api_key, right_id, right_book, request.chapter)

    common_verse_numbers = sorted(set(left_verses.keys()) & set(right_verses.keys()))
    common_verse_numbers = [
        verse_number
        for verse_number in common_verse_numbers
        if verse_number >= request.start_verse
        and (request.end_verse is None or verse_number <= request.end_verse)
    ]

    if not common_verse_numbers:
        raise ValueError(
            f"No overlapping verses found between {request.left_version} and "
            f"{request.right_version} for {request.book} {request.chapter}."
        )

    _report(progress_callback, 92, "Preparing matched verses...")
    return left_verses, right_verses, common_verse_numbers


def build_verses_preview(request: VersesGenerateRequest, progress_callback: ProgressCallback = None) -> VersesPreviewResponse:
    left_verses, right_verses, common_verse_numbers = _load_verses(request, progress_callback=progress_callback)

    if request.template_path:
        presentation_mode = "powerpoint-template"
    elif request.background_image_path:
        presentation_mode = "image-background"
    else:
        try:
            get_default_verses_template()
            presentation_mode = "bundled-template"
        except FileNotFoundError:
            presentation_mode = "portable"

    response = VersesPreviewResponse(
        presentation_mode=presentation_mode,
        book=request.book,
        chapter=request.chapter,
        left_version=request.left_version,
        right_version=request.right_version,
        verse_count=len(common_verse_numbers),
        verses=[
            VersePreviewItem(
                verse_number=verse_number,
                left_text=left_verses[verse_number],
                right_text=right_verses[verse_number],
            )
            for verse_number in common_verse_numbers
        ],
    )
    _report(progress_callback, 100, "Verses preview ready.")
    return response


def _build_verses_output_path() -> Path:
    BACKEND_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    base_name = datetime.now().strftime("%B-%d-%Y")
    output_path = BACKEND_OUTPUT_DIR / f"{base_name}.pptx"
    suffix = 2

    while output_path.exists():
        output_path = BACKEND_OUTPUT_DIR / f"{base_name}-{suffix}.pptx"
        suffix += 1

    return output_path


def generate_verses_ppt(request: VersesGenerateRequest, progress_callback: ProgressCallback = None) -> Path:
    settings = load_settings()
    _report(progress_callback, 6, "Preparing verse export...")
    left_verses, right_verses, verse_numbers = _load_verses(request, progress_callback=progress_callback)
    if request.template_path:
        template_path = resolve_verses_template(request.template_path)
    else:
        try:
            template_path = get_default_verses_template()
        except FileNotFoundError:
            template_path = None
    background_image_path = resolve_background_image_path(request.background_image_path)
    output_path = _build_verses_output_path()
    _report(progress_callback, 94, "Rendering PowerPoint slides...")

    if request.template_path and settings.enable_legacy_templates and settings.ppt_engine == "legacy":
        create_verses_presentation_legacy(
            template_path=template_path,
            output_path=output_path,
            book=request.book,
            chapter=request.chapter,
            left_verses=left_verses,
            right_verses=right_verses,
            left_label=request.left_version,
            right_label=request.right_version,
            start_verse=request.start_verse,
            end_verse=request.end_verse,
        )
    else:
        create_verses_presentation_portable(
            output_path=output_path,
            book=request.book,
            chapter=request.chapter,
            left_label=request.left_version,
            right_label=request.right_version,
            left_verses=left_verses,
            right_verses=right_verses,
            verse_numbers=verse_numbers,
            template_ppt_path=template_path,
            background_image_path=background_image_path,
            header_font_name=request.header_font_name,
            verse_font_name=request.verse_font_name,
            header_font_color=request.header_font_color,
            verse_font_color=request.verse_font_color,
        )
    _report(progress_callback, 100, "Verses PowerPoint ready.")
    return output_path
