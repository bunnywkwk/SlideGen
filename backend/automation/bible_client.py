import html
import re
from typing import Dict, Optional, Sequence, Tuple, Union

import requests


BASE_URL = "https://api.youversion.com/v1"
BOOK_ALIASES = {
    "genesis": "GEN",
    "exodus": "EXO",
    "leviticus": "LEV",
    "numbers": "NUM",
    "deuteronomy": "DEU",
    "joshua": "JOS",
    "judges": "JDG",
    "ruth": "RUT",
    "1samuel": "1SA",
    "1stsamuel": "1SA",
    "firstsamuel": "1SA",
    "2samuel": "2SA",
    "2ndsamuel": "2SA",
    "secondsamuel": "2SA",
    "1kings": "1KI",
    "1stkings": "1KI",
    "firstkings": "1KI",
    "2kings": "2KI",
    "2ndkings": "2KI",
    "secondkings": "2KI",
    "1chronicles": "1CH",
    "1stchronicles": "1CH",
    "firstchronicles": "1CH",
    "2chronicles": "2CH",
    "2ndchronicles": "2CH",
    "secondchronicles": "2CH",
    "ezra": "EZR",
    "nehemiah": "NEH",
    "esther": "EST",
    "job": "JOB",
    "psalm": "PSA",
    "psalms": "PSA",
    "proverbs": "PRO",
    "ecclesiastes": "ECC",
    "songofsolomon": "SNG",
    "songofsongs": "SNG",
    "songofsong": "SNG",
    "isaiah": "ISA",
    "jeremiah": "JER",
    "lamentations": "LAM",
    "ezekiel": "EZK",
    "daniel": "DAN",
    "hosea": "HOS",
    "joel": "JOL",
    "amos": "AMO",
    "obadiah": "OBA",
    "jonah": "JON",
    "micah": "MIC",
    "nahum": "NAM",
    "habakkuk": "HAB",
    "zephaniah": "ZEP",
    "haggai": "HAG",
    "zechariah": "ZEC",
    "malachi": "MAL",
    "matthew": "MAT",
    "mark": "MRK",
    "luke": "LUK",
    "john": "JHN",
    "acts": "ACT",
    "romans": "ROM",
    "1corinthians": "1CO",
    "1stcorinthians": "1CO",
    "firstcorinthians": "1CO",
    "2corinthians": "2CO",
    "2ndcorinthians": "2CO",
    "secondcorinthians": "2CO",
    "galatians": "GAL",
    "ephesians": "EPH",
    "philippians": "PHP",
    "colossians": "COL",
    "1thessalonians": "1TH",
    "1stthessalonians": "1TH",
    "firstthessalonians": "1TH",
    "2thessalonians": "2TH",
    "2ndthessalonians": "2TH",
    "secondthessalonians": "2TH",
    "1timothy": "1TI",
    "1sttimothy": "1TI",
    "firsttimothy": "1TI",
    "2timothy": "2TI",
    "2ndtimothy": "2TI",
    "secondtimothy": "2TI",
    "titus": "TIT",
    "philemon": "PHM",
    "hebrews": "HEB",
    "james": "JAS",
    "1peter": "1PE",
    "1stpeter": "1PE",
    "firstpeter": "1PE",
    "2peter": "2PE",
    "2ndpeter": "2PE",
    "secondpeter": "2PE",
    "1john": "1JN",
    "1stjohn": "1JN",
    "firstjohn": "1JN",
    "2john": "2JN",
    "2ndjohn": "2JN",
    "secondjohn": "2JN",
    "3john": "3JN",
    "3rdjohn": "3JN",
    "thirdjohn": "3JN",
    "jude": "JUD",
    "revelation": "REV",
}

ParamsType = Optional[Union[Dict[str, str], Sequence[Tuple[str, str]]]]


def strip_html(text: str) -> str:
    clean = re.sub(r"<[^>]+>", "", html.unescape(text or ""))
    return re.sub(r"\s+", " ", clean).strip()


def normalize_book_token(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (value or "").lower())


def _request_with_header(path: str, api_key: str, header_name: str, params: ParamsType = None):
    headers = {header_name: api_key}
    return requests.get(f"{BASE_URL}{path}", headers=headers, params=params, timeout=30)


def api_get(path: str, api_key: str, params: ParamsType = None):
    response = _request_with_header(path, api_key, "X-YVP-App-Key", params=params)
    if response.status_code == 401:
        response = _request_with_header(path, api_key, "api-key", params=params)

    response.raise_for_status()
    payload = response.json()
    if isinstance(payload, dict) and "data" in payload:
        return payload["data"]
    return payload


def fetch_bible_options(api_key: str, language_ranges: str):
    ranges = [item.strip() for item in language_ranges.split(",") if item.strip()]
    params = [("language_ranges[]", item) for item in ranges] if ranges else [("language_ranges[]", "*")]
    return api_get("/bibles", api_key, params=params)


def _find_bible_in_list(bibles, wanted: str):
    wanted_lower = wanted.lower()
    for bible in bibles:
        abbr = (bible.get("abbreviation") or bible.get("abbr") or "").lower()
        name = (bible.get("name") or bible.get("title") or bible.get("localized_title") or "").lower()
        if wanted_lower in abbr or wanted_lower in name:
            return bible.get("id") or bible.get("version_id")
    return None


def find_bible_id(api_key: str, wanted: str, language_ranges: str):
    candidate_ranges = [language_ranges, "en,tl,ceb,hil", "en", "tl", "ceb", "hil", "*"]
    seen = set()
    last_bibles = []

    for spec in candidate_ranges:
        if spec in seen:
            continue
        seen.add(spec)
        bibles = fetch_bible_options(api_key, spec)
        last_bibles = bibles
        bible_id = _find_bible_in_list(bibles, wanted)
        if bible_id is not None:
            return bible_id

    available = ", ".join(sorted((b.get("abbreviation") or "") for b in last_bibles if b.get("abbreviation")))
    raise ValueError(
        f"Bible version not found: {wanted}. Last discovered abbreviations: {available}. "
        "Try using the exact abbreviation shown by your account's /bibles response."
    )


def find_book_usfm(api_key: str, bible_id, book_name: str) -> str:
    target = normalize_book_token(book_name)
    books = api_get(f"/bibles/{bible_id}/books", api_key)
    available_ids = {str(book.get("id") or "").upper() for book in books}

    alias_usfm = BOOK_ALIASES.get(target)
    if alias_usfm and alias_usfm in available_ids:
        return alias_usfm

    for book in books:
        usfm = str(book.get("usfm") or book.get("book_usfm") or book.get("id") or "").upper()
        name = normalize_book_token(book.get("name") or book.get("title") or "")
        full_title = normalize_book_token(book.get("full_title") or "")
        short = normalize_book_token(book.get("abbreviation") or book.get("abbr") or "")
        usfm_norm = normalize_book_token(usfm)

        if target in {usfm_norm, short, name, full_title}:
            return usfm
        if target.rstrip("s") in {name.rstrip("s"), full_title.rstrip("s")}:
            return usfm

    available_sample = ", ".join(sorted(list(available_ids))[:12])
    raise ValueError(
        f"Book not found in selected Bible: {book_name}. "
        f"Available book IDs include: {available_sample}"
    )


def get_verses(api_key: str, bible_id, book_usfm: str, chapter_number: int) -> Dict[int, str]:
    verse_rows = api_get(f"/bibles/{bible_id}/books/{book_usfm}/chapters/{chapter_number}/verses", api_key)
    verses: Dict[int, str] = {}

    for row in verse_rows:
        ref = str(row.get("reference") or "")
        number = (
            row.get("verse")
            or row.get("number")
            or row.get("verse_number")
            or row.get("title")
            or row.get("id")
        )
        if number is None and ":" in ref:
            number = ref.split(":")[-1]
        if number is None:
            continue

        try:
            number_int = int(str(number).strip())
        except ValueError:
            continue

        passage_id = row.get("passage_id")
        if not passage_id:
            continue

        passage = api_get(f"/bibles/{bible_id}/passages/{passage_id}", api_key, params={"format": "text"})
        verses[number_int] = strip_html(str(passage.get("content") or ""))

    return verses
