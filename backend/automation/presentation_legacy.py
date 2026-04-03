from pathlib import Path

from .legacy_loader import load_lyrics_core, load_verses_core


def create_lyrics_presentation(
    template_path: Path,
    output_path: Path,
    songs,
    include_welcome_slide: bool,
    include_verse_labels: bool,
) -> None:
    core = load_lyrics_core()
    core.create_presentation(
        template_path=template_path,
        output_path=output_path,
        songs=songs,
        include_welcome_slide=include_welcome_slide,
        include_verse_labels=include_verse_labels,
    )


def create_verses_presentation(
    template_path: Path,
    output_path: Path,
    book: str,
    chapter: int,
    left_verses: dict[int, str],
    right_verses: dict[int, str],
    left_label: str,
    right_label: str,
    start_verse: int,
    end_verse: int | None,
) -> None:
    core = load_verses_core()
    core.create_deck(
        template_path=str(template_path),
        out_path=str(output_path),
        book=book,
        chapter=chapter,
        niv_verses=left_verses,
        mbb_verses=right_verses,
        left_label=left_label,
        right_label=right_label,
        start_verse=start_verse,
        end_verse=end_verse,
    )
