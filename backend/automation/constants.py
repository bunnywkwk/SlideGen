from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = PROJECT_ROOT / "backend"
BACKEND_OUTPUT_DIR = BACKEND_ROOT / "output"
BACKEND_UPLOAD_DIR = BACKEND_ROOT / "uploads"
LEGACY_LYRICS_DIR = PROJECT_ROOT / "lyrics-generator"
LEGACY_VERSES_DIR = PROJECT_ROOT / "verse-generator"
DEFAULT_LYRICS_SONG_SLOTS = 3
DEFAULT_LEFT_VERSION = "NIV11"
DEFAULT_RIGHT_VERSION = "APD"
DEFAULT_LANGUAGE_RANGES = "*"

BOOK_OPTIONS = [
    "Genesis",
    "Exodus",
    "Leviticus",
    "Numbers",
    "Deuteronomy",
    "Joshua",
    "Judges",
    "Ruth",
    "1 Samuel",
    "2 Samuel",
    "1 Kings",
    "2 Kings",
    "1 Chronicles",
    "2 Chronicles",
    "Ezra",
    "Nehemiah",
    "Esther",
    "Job",
    "Psalm",
    "Proverbs",
    "Ecclesiastes",
    "Song of Solomon",
    "Isaiah",
    "Jeremiah",
    "Lamentations",
    "Ezekiel",
    "Daniel",
    "Hosea",
    "Joel",
    "Amos",
    "Obadiah",
    "Jonah",
    "Micah",
    "Nahum",
    "Habakkuk",
    "Zephaniah",
    "Haggai",
    "Zechariah",
    "Malachi",
    "Matthew",
    "Mark",
    "Luke",
    "John",
    "Acts",
    "Romans",
    "1 Corinthians",
    "2 Corinthians",
    "Galatians",
    "Ephesians",
    "Philippians",
    "Colossians",
    "1 Thessalonians",
    "2 Thessalonians",
    "1 Timothy",
    "2 Timothy",
    "Titus",
    "Philemon",
    "Hebrews",
    "James",
    "1 Peter",
    "2 Peter",
    "1 John",
    "2 John",
    "3 John",
    "Jude",
    "Revelation",
]

DEFAULT_VERSION_OPTIONS = [
    "NIV11",
    "NKJV",
    "ESV",
    "NLT",
    "KJV",
    "AMP",
    "NASB",
    "MSG",
    "APD",
    "MBBTAG",
    "ASND",
    "RCPV",
]


def resolve_project_path(raw_path: str) -> Path:
    """Resolve a user path, treating relative paths as relative to the project root."""
    path = Path(raw_path).expanduser()
    if path.is_absolute():
        return path
    return (PROJECT_ROOT / path).resolve()
