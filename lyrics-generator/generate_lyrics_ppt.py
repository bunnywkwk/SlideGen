import argparse
import re
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

import pythoncom
import win32com.client as win32


SLIDE_BREAK = "__SLIDE_BREAK__"
MIDDLE_ANCHOR = 3
CENTER_ALIGN = 2
TOP_ANCHOR = 1
SECTION_LABELS = {
    "chorus": "CHORUS:",
    "bridge": "BRIDGE:",
    "verse": None,
    "intro": "INTRO:",
    "outro": "OUTRO:",
    "tag": "TAG:",
    "refrain": "REFRAIN:",
}


@dataclass
class Section:
    name: str
    lines: List[str]


@dataclass
class Song:
    title: str
    source_path: Path
    sections: List[Section]


@dataclass
class SlideChunk:
    song_title: str
    section_name: str
    lines: List[str]
    section_label: Optional[str]


def display_section_name(section_name: str) -> str:
    normalized = normalize_section_name(section_name)
    if normalized.startswith("pre-chorus") or normalized.startswith("pre chorus") or normalized.startswith("prechorus"):
        suffix = normalized.replace("pre-chorus", "").replace("pre chorus", "").replace("prechorus", "").strip()
        return f"Pre-Chorus {suffix}".strip()
    return normalized.title() if normalized else "Verse"


def parse_song_text(text: str, source_name: str = "Pasted Song", title_hint: Optional[str] = None) -> Song:
    text = normalize_text_artifacts(text or "")
    raw_lines = [line.rstrip() for line in text.splitlines()]

    title = normalize_line(title_hint or "") or slug_to_title(Path(source_name).stem)
    sections: List[Section] = []
    current_name = "verse"
    current_lines: List[str] = []
    saw_content = False

    for raw_line in raw_lines:
        line = normalize_line(raw_line)
        if not line:
            continue

        title_match = re.match(r"^(?:title|song)\s*:\s*(.+)$", line, re.IGNORECASE)
        if title_match:
            title = title_match.group(1).strip()
            continue

        if line == "---":
            if current_lines and current_lines[-1] != SLIDE_BREAK:
                current_lines.append(SLIDE_BREAK)
            continue

        heading_match = re.match(r"^\[(.+?)\]$", line) or (re.match(r"^(.+)$", line) if is_section_heading(line) else None)
        if heading_match and is_section_heading(heading_match.group(1)):
            if current_lines:
                sections.append(Section(name=current_name, lines=current_lines))
                current_lines = []
            current_name = normalize_section_name(heading_match.group(1))
            continue

        if not saw_content and not sections and not current_lines:
            if is_metadata_line(line):
                continue
            if line.isupper() and len(line) > 4 and not is_section_heading(line) and not title_hint:
                title = normalize_text_artifacts(line).title()
                continue

        current_lines.append(line)
        saw_content = True

    if current_lines:
        sections.append(Section(name=current_name, lines=current_lines))

    if not sections:
        raise ValueError(f"No lyric lines found in {source_name}")

    return Song(title=title, source_path=Path(source_name), sections=sections)


def slug_to_title(stem: str) -> str:
    cleaned = re.sub(r"[_-]+", " ", stem).strip()
    cleaned = re.sub(r"\s+", " ", cleaned)
    cleaned = re.sub(r"([a-z])([A-Z])", r"\1 \2", cleaned)
    return cleaned.title() if cleaned else stem


def normalize_line(line: str) -> str:
    return re.sub(r"\s+", " ", line.strip())


def normalize_section_name(name: str) -> str:
    stripped = normalize_line(name).strip(":")
    return stripped.lower()


def normalize_text_artifacts(text: str) -> str:
    replacements = {
        "â€™": "’",
        "â€˜": "‘",
        "â€œ": '"',
        "â€\x9d": '"',
        "Â©": "",
        "ð\x9d\x98³ð\x9d\x98¦ð\x9d\x98±ð\x9d\x98¦ð\x9d\x98¢ð\x9d\x98µ": "",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text


def is_section_heading(line: str) -> bool:
    normalized = normalize_section_name(line.strip("[]"))
    if normalized in SECTION_LABELS:
        return True
    return bool(re.match(r"^(pre[- ]?chorus|verse|bridge|chorus|intro|outro|tag|refrain)( \d+)?$", normalized))


def is_metadata_line(line: str) -> bool:
    lowered = line.lower()
    return (
        lowered.startswith("copyright")
        or lowered.startswith("words and music by")
        or lowered.startswith("written by")
        or lowered.startswith("ccli")
        or "integrity" in lowered
        or "hosanna" in lowered
        or lowered.startswith("©")
    )


def parse_song_file(path: Path) -> Song:
    return parse_song_text(path.read_text(encoding="utf-8"), source_name=str(path), title_hint=None)


def validate_song_text(text: str, title_hint: Optional[str] = None) -> List[str]:
    warnings: List[str] = []
    normalized = normalize_text_artifacts(text or "")
    lines = [normalize_line(line) for line in normalized.splitlines() if normalize_line(line)]
    lowered_lines = [line.lower() for line in lines]

    if not normalize_line(title_hint or "") and not any(re.match(r"^(?:title|song)\s*:", line, re.IGNORECASE) for line in lines):
        warnings.append("Missing title field")
    if not any(is_section_heading(line.strip("[]")) for line in lines):
        warnings.append("No section headers detected")
    if any("http://" in line or "https://" in line or "www." in line.lower() for line in lines):
        warnings.append("Contains URL text")
    if any(is_metadata_line(line) for line in lines):
        warnings.append("Contains metadata or copyright text")
    chord_pattern = re.compile(r"^[A-G](?:#|b)?(?:m|maj|min|sus|dim|aug)?\d?(?:/[A-G](?:#|b)?)?$")
    if any(chord_pattern.match(line) for line in lines):
        warnings.append("Contains possible chord lines")
    if not any(line and line != "---" and not is_section_heading(line.strip("[]")) for line in lines):
        warnings.append("No lyric lines detected")

    try:
        song = parse_song_text(normalized, source_name="Validation", title_hint=title_hint)
        if len(build_song_chunks(song)) > 18:
            warnings.append("Large song: many lyric slides")
    except Exception as err:
        warnings.append(str(err))

    return warnings


def estimate_line_weight(line: str) -> int:
    return len(re.sub(r"\s+", "", line))


def choose_chunk_size(lines: List[str], start_index: int) -> int:
    remaining = lines[start_index:]
    if len(remaining) <= 2:
        return len(remaining)

    next_four = remaining[:4]

    if len(next_four) == 4 and max(estimate_line_weight(line) for line in next_four) <= 16:
        return 4
    if max(estimate_line_weight(line) for line in remaining[:2]) <= 30:
        return 2
    if len(remaining) >= 3 and max(estimate_line_weight(line) for line in remaining[:3]) <= 22:
        return 3
    return 2


def format_section_label(section_name: str) -> Optional[str]:
    normalized = normalize_section_name(section_name)
    if normalized == "verse":
        return None
    if normalized in SECTION_LABELS:
        return SECTION_LABELS[normalized]
    if normalized.startswith("pre-chorus") or normalized.startswith("pre chorus") or normalized.startswith("prechorus"):
        suffix = normalized.replace("pre-chorus", "").replace("pre chorus", "").replace("prechorus", "").strip()
        return f"PRE-CHORUS {suffix}:".replace("  ", " ").replace(" :", ":")
    return f"{normalized.upper()}:"


def section_label_for(section_name: str, include_verse_labels: bool) -> Optional[str]:
    normalized = normalize_section_name(section_name)
    if normalized == "verse" and include_verse_labels:
        return "VERSE:"
    return format_section_label(section_name)


def split_on_manual_breaks(lines: List[str]) -> List[List[str]]:
    groups: List[List[str]] = []
    current: List[str] = []
    for line in lines:
        if line == SLIDE_BREAK:
            if current:
                groups.append(current)
                current = []
            continue
        current.append(line)
    if current:
        groups.append(current)
    return groups


def build_song_chunks(song: Song, include_verse_labels: bool = False) -> List[SlideChunk]:
    chunks: List[SlideChunk] = []
    for section in song.sections:
        label = section_label_for(section.name, include_verse_labels)
        for group in split_on_manual_breaks(section.lines):
            index = 0
            while index < len(group):
                if len(group) <= 4:
                    chunk_lines = group[index:]
                    index = len(group)
                else:
                    chunk_size = choose_chunk_size(group, index)
                    chunk_lines = group[index:index + chunk_size]
                    index += chunk_size
                chunks.append(
                    SlideChunk(
                        song_title=song.title,
                        section_name=section.name,
                        lines=chunk_lines,
                        section_label=label,
                    )
                )
    return chunks


def song_to_draft_text(song: Song) -> str:
    lines: List[str] = []
    for section in song.sections:
        groups = split_on_manual_breaks(section.lines)
        chunk_texts: List[List[str]] = []
        for group in groups:
            index = 0
            while index < len(group):
                if len(group) <= 4:
                    chunk_lines = group[index:]
                    index = len(group)
                else:
                    chunk_size = choose_chunk_size(group, index)
                    chunk_lines = group[index:index + chunk_size]
                    index += chunk_size
                chunk_texts.append(chunk_lines)

        if lines:
            lines.append("")
        lines.append(f"[{display_section_name(section.name)}]")
        for chunk_index, chunk_lines in enumerate(chunk_texts):
            if chunk_index > 0:
                lines.append("---")
            lines.extend(chunk_lines)

    return "\n".join(lines).strip()


def iter_song_files(input_dir: Path) -> Iterable[Path]:
    return sorted(path for path in input_dir.glob("*.txt") if path.is_file())


def load_songs(input_dir: Path) -> List[Song]:
    songs = [parse_song_file(path) for path in iter_song_files(input_dir)]
    if not songs:
        raise ValueError(f"No .txt lyric files found in {input_dir}")
    return songs


def group_batches(songs: List[Song], songs_per_ppt: int) -> List[List[Song]]:
    return [songs[i:i + songs_per_ppt] for i in range(0, len(songs), songs_per_ppt)]


def template_sort_key(path: Path):
    for fmt in ("%B-%d-%Y", "%B-%d-%y", "%B-%-d-%y"):
        try:
            parsed = datetime.strptime(path.stem, fmt)
            return (1, parsed)
        except ValueError:
            continue
    return (0, datetime.min)


def resolve_template(template: Optional[Path], samples_dir: Path) -> Path:
    if template:
        if not template.exists():
            raise FileNotFoundError(f"Template not found: {template}")
        return template

    candidates = sorted(samples_dir.glob("*.pptx"))
    if not candidates:
        raise FileNotFoundError(f"No sample PPTX files found in {samples_dir}")
    return max(candidates, key=template_sort_key)


def unique_output_path(out_dir: Path, batch_index: int) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%B-%d-%Y")
    candidate = out_dir / f"{stamp}-lyrics-batch-{batch_index}.pptx"
    counter = 2
    while candidate.exists():
        candidate = out_dir / f"{stamp}-lyrics-batch-{batch_index}-{counter}.pptx"
        counter += 1
    return candidate


def ensure_text(text_value: str) -> str:
    return text_value if text_value else " "


def text_shapes(slide):
    shapes = []
    for idx in range(1, slide.Shapes.Count + 1):
        shape = slide.Shapes(idx)
        try:
            if shape.HasTextFrame and shape.TextFrame:
                shapes.append(shape)
        except Exception:
            continue
    return shapes


def primary_text_shape(slide):
    candidates = []
    for shape in text_shapes(slide):
        try:
            area = float(shape.Width) * float(shape.Height)
            text = normalize_line(shape.TextFrame.TextRange.Text.replace("\r", " "))
        except Exception:
            area = 0
            text = ""
        candidates.append((area, len(text), shape))
    if not candidates:
        raise ValueError("No text shapes found on template slide")
    candidates.sort(key=lambda item: (item[0], item[1]), reverse=True)
    return candidates[0][2]


def secondary_text_shape(slide):
    candidates = []
    for shape in text_shapes(slide):
        try:
            area = float(shape.Width) * float(shape.Height)
            top = float(shape.Top)
            left = float(shape.Left)
            text = normalize_line(shape.TextFrame.TextRange.Text.replace("\r", " "))
        except Exception:
            continue
        candidates.append((area, top, left, len(text), shape))
    if len(candidates) < 2:
        return None
    candidates.sort(key=lambda item: (item[0], item[1], item[2], -item[3]))
    return candidates[0][4]


def set_shape_text(shape, text: str) -> None:
    shape.TextFrame.TextRange.Text = ensure_text(text)


def center_main_text_shape(shape) -> None:
    try:
        shape.TextFrame.MarginTop = 0
        shape.TextFrame.MarginBottom = 0
        shape.TextFrame.MarginLeft = 0
        shape.TextFrame.MarginRight = 0
        shape.TextFrame.VerticalAnchor = MIDDLE_ANCHOR
        shape.TextFrame.TextRange.ParagraphFormat.Alignment = CENTER_ALIGN
    except Exception:
        pass


def pin_section_label_shape(shape) -> None:
    if shape is None:
        return
    try:
        shape.TextFrame.VerticalAnchor = TOP_ANCHOR
    except Exception:
        pass


def append_duplicate_slide(presentation, prototype_slide):
    duplicated = prototype_slide.Duplicate().Item(1)
    duplicated.MoveTo(presentation.Slides.Count)
    return duplicated


def render_title_slide(slide, song_title: str) -> None:
    title_shape = primary_text_shape(slide)
    set_shape_text(title_shape, song_title.upper())
    center_main_text_shape(title_shape)


def render_lyric_slide(slide, chunk: SlideChunk) -> None:
    lyric_shape = primary_text_shape(slide)
    section_shape = secondary_text_shape(slide)
    set_shape_text(lyric_shape, "\r".join(chunk.lines))
    center_main_text_shape(lyric_shape)
    if section_shape is not None:
        set_shape_text(section_shape, chunk.section_label or "")
        pin_section_label_shape(section_shape)


def slide_paragraphs(shape) -> List[str]:
    try:
        text_range = shape.TextFrame.TextRange
    except Exception:
        return []
    paragraphs = []
    for idx in range(1, text_range.Paragraphs().Count + 1):
        paragraph = normalize_line(text_range.Paragraphs(idx).Text.replace("\r", " "))
        if paragraph:
            paragraphs.append(paragraph)
    return paragraphs


def prototype_signature(slide) -> Tuple[int, bool, bool]:
    shapes = text_shapes(slide)
    if not shapes:
        return (0, False, False)
    main_shape = primary_text_shape(slide)
    main_lines = len(slide_paragraphs(main_shape))
    extra_shape = secondary_text_shape(slide)
    has_label = False
    if extra_shape is not None:
        label_text = normalize_line(extra_shape.TextFrame.TextRange.Text.replace("\r", " "))
        has_label = label_text.endswith(":")
    title_like = len(shapes) == 1 and main_lines == 1
    return (main_lines, has_label, title_like)


def build_prototype_catalog(presentation) -> Dict[str, object]:
    catalog: Dict[str, object] = {}
    lyric_candidates: Dict[Tuple[int, bool], object] = {}

    for index in range(1, presentation.Slides.Count + 1):
        slide = presentation.Slides(index)
        main_lines, has_label, title_like = prototype_signature(slide)
        if title_like:
            title_text = normalize_line(primary_text_shape(slide).TextFrame.TextRange.Text.replace("\r", " "))
            if title_text != "WELCOME" and "title" not in catalog:
                catalog["title"] = slide
        if main_lines >= 1 and not title_like:
            lyric_candidates.setdefault((main_lines, has_label), slide)

    if "title" not in catalog:
        raise ValueError("Could not find a title-slide prototype in the sample PPT")

    for key, slide in lyric_candidates.items():
        catalog[f"lyric:{key[0]}:{int(key[1])}"] = slide

    return catalog


def choose_lyric_prototype(catalog: Dict[str, object], chunk: SlideChunk):
    line_count = len(chunk.lines)
    has_label = bool(chunk.section_label)
    preferred_keys = [
        f"lyric:{line_count}:{int(has_label)}",
        f"lyric:{line_count}:0",
        f"lyric:{line_count}:1",
    ]
    if line_count == 1:
        preferred_keys.extend(["lyric:2:1", "lyric:2:0"])
    if line_count == 3:
        preferred_keys.extend([f"lyric:2:{int(has_label)}", f"lyric:4:{int(has_label)}"])
    if line_count == 4:
        preferred_keys.extend(["lyric:3:1", "lyric:3:0"])
    if line_count == 2:
        preferred_keys.extend(["lyric:3:0", "lyric:3:1"])

    seen = set()
    for key in preferred_keys:
        if key in seen:
            continue
        seen.add(key)
        slide = catalog.get(key)
        if slide is not None:
            return slide

    for key, slide in catalog.items():
        if key.startswith("lyric:"):
            return slide
    raise ValueError("Could not find any lyric-slide prototype in the sample PPT")


def create_presentation(
    template_path: Path,
    output_path: Path,
    songs: List[Song],
    include_welcome_slide: bool,
    include_verse_labels: bool,
) -> None:
    pythoncom.CoInitialize()
    app = None
    presentation = None

    try:
        app = win32.Dispatch("PowerPoint.Application")
        app.Visible = True
        presentation = app.Presentations.Open(str(template_path), WithWindow=False)
        original_slide_count = presentation.Slides.Count
        catalog = build_prototype_catalog(presentation)
        title_prototype = catalog["title"]

        for song in songs:
            title_slide = append_duplicate_slide(presentation, title_prototype)
            render_title_slide(title_slide, song.title)

            for chunk in build_song_chunks(song, include_verse_labels=include_verse_labels):
                lyric_prototype = choose_lyric_prototype(catalog, chunk)
                lyric_slide = append_duplicate_slide(presentation, lyric_prototype)
                render_lyric_slide(lyric_slide, chunk)

        if include_welcome_slide and original_slide_count >= 1:
            for idx in range(original_slide_count, 1, -1):
                presentation.Slides(idx).Delete()
        else:
            for idx in range(original_slide_count, 0, -1):
                presentation.Slides(idx).Delete()

        presentation.SaveAs(str(output_path))
    finally:
        if presentation is not None:
            presentation.Close()
        if app is not None:
            app.Quit()
        pythoncom.CoUninitialize()


def dry_run_report(batches: List[List[Song]], include_verse_labels: bool) -> str:
    lines = []
    for batch_index, songs in enumerate(batches, start=1):
        lines.append(f"Batch {batch_index}: {len(songs)} song(s)")
        for song in songs:
            chunks = build_song_chunks(song, include_verse_labels=include_verse_labels)
            slide_count = 1 + len(chunks)
            lines.append(f"  - {song.title}: {slide_count} generated slide(s)")
            for chunk in chunks:
                label = f" [{chunk.section_label}]" if chunk.section_label else ""
                joined = " / ".join(chunk.lines)
                lines.append(f"      {joined}{label}")
    return "\n".join(lines)


def main() -> None:
    base_dir = Path(__file__).resolve().parent

    parser = argparse.ArgumentParser(description="Generate lyric PowerPoint decks from .txt song files.")
    parser.add_argument("--input-dir", type=Path, default=base_dir / "txt-lyrics", help="Folder containing lyric .txt files")
    parser.add_argument("--samples-dir", type=Path, default=base_dir / "samples-ppt", help="Folder containing sample PPTX files")
    parser.add_argument("--template", type=Path, default=None, help="Specific sample PPTX to use as the visual template")
    parser.add_argument("--out-dir", type=Path, default=base_dir / "generated-ppt", help="Folder for generated PPTX files")
    parser.add_argument("--songs-per-ppt", type=int, default=4, choices=[1, 2, 3, 4], help="How many songs to place in one PPT")
    parser.add_argument("--include-welcome-slide", action="store_true", help="Keep the original welcome slide from the sample deck")
    parser.add_argument("--include-verse-labels", action="store_true", help="Show VERSE: labels as well as chorus/bridge labels")
    parser.add_argument("--dry-run", action="store_true", help="Analyze files and batching without opening PowerPoint")
    args = parser.parse_args()

    try:
        songs = load_songs(args.input_dir)
        template_path = resolve_template(args.template, args.samples_dir)
        batches = group_batches(songs, args.songs_per_ppt)

        if args.dry_run:
            print(f"Template: {template_path}")
            print(dry_run_report(batches, include_verse_labels=args.include_verse_labels))
            return

        generated_files: List[Path] = []
        for batch_index, song_batch in enumerate(batches, start=1):
            output_path = unique_output_path(args.out_dir, batch_index)
            create_presentation(
                template_path=template_path,
                output_path=output_path,
                songs=song_batch,
                include_welcome_slide=args.include_welcome_slide,
                include_verse_labels=args.include_verse_labels,
            )
            generated_files.append(output_path)

        for path in generated_files:
            print(f"Created: {path}")
    except Exception as err:
        print(f"Error: {err}")
        sys.exit(1)


if __name__ == "__main__":
    main()
