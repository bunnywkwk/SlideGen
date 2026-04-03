import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, Optional


SLIDE_BREAK = "__SLIDE_BREAK__"
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
    lines: list[str]


@dataclass
class Song:
    title: str
    source_path: Path
    sections: list[Section]


@dataclass
class SlideChunk:
    song_title: str
    section_name: str
    lines: list[str]
    section_label: str | None


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
    sections: list[Section] = []
    current_name = "verse"
    current_lines: list[str] = []
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


def parse_song_file(path: Path) -> Song:
    return parse_song_text(path.read_text(encoding="utf-8"), source_name=str(path), title_hint=None)


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
        "Ã¢â‚¬â„¢": "’",
        "Ã¢â‚¬Ëœ": "‘",
        "Ã¢â‚¬Å“": '"',
        "Ã¢â‚¬\x9d": '"',
        "Ã‚Â©": "",
        "Ã°\x9d\x98Â³Ã°\x9d\x98Â¦Ã°\x9d\x98Â±Ã°\x9d\x98Â¦Ã°\x9d\x98Â¢Ã°\x9d\x98Âµ": "",
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
        or lowered.startswith("â©")
    )


def validate_song_text(text: str, title_hint: Optional[str] = None) -> list[str]:
    warnings: list[str] = []
    normalized = normalize_text_artifacts(text or "")
    lines = [normalize_line(line) for line in normalized.splitlines() if normalize_line(line)]

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


def choose_chunk_size(lines: list[str], start_index: int) -> int:
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


def format_section_label(section_name: str) -> str | None:
    normalized = normalize_section_name(section_name)
    if normalized == "verse":
        return None
    if normalized in SECTION_LABELS:
        return SECTION_LABELS[normalized]
    if normalized.startswith("pre-chorus") or normalized.startswith("pre chorus") or normalized.startswith("prechorus"):
        suffix = normalized.replace("pre-chorus", "").replace("pre chorus", "").replace("prechorus", "").strip()
        return f"PRE-CHORUS {suffix}:".replace("  ", " ").replace(" :", ":")
    return f"{normalized.upper()}:"


def section_label_for(section_name: str, include_verse_labels: bool) -> str | None:
    normalized = normalize_section_name(section_name)
    if normalized == "verse" and include_verse_labels:
        return "VERSE:"
    return format_section_label(section_name)


def split_on_manual_breaks(lines: list[str]) -> list[list[str]]:
    groups: list[list[str]] = []
    current: list[str] = []
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


def build_song_chunks(song: Song, include_verse_labels: bool = False) -> list[SlideChunk]:
    chunks: list[SlideChunk] = []
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
    lines: list[str] = []
    for section in song.sections:
        groups = split_on_manual_breaks(section.lines)
        chunk_texts: list[list[str]] = []
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


def load_songs(input_dir: Path) -> list[Song]:
    songs = [parse_song_file(path) for path in iter_song_files(input_dir)]
    if not songs:
        raise ValueError(f"No .txt lyric files found in {input_dir}")
    return songs


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
