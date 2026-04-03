# Lyrics PPT Generator

This folder now includes a Python generator for church lyric PowerPoint decks based on the sample slides in `samples-ppt`.

## What It Does

- Reads song lyrics from `txt-lyrics`
- Supports a paste-first desktop GUI for 1st through 4th song entry
- Groups `3` or `4` songs into one output deck
- Creates a title slide for each song
- Splits lyrics into multiple slides using the sample style
- Reuses the sample PPT as the visual template
- Preserves section labels like `CHORUS:` and `BRIDGE:`

## Expected Lyric Format

Each `.txt` file is one song.

Example:

```text
Title: God Is Good

[Verse]
God is good all the time
He put a song of praise
In this heart of mine

[Chorus]
God is good all the time
Through the darkest night
His light will shine
```

Notes:

- `Title:` is optional. If missing, the filename is used.
- Section headers like `[Verse]`, `[Chorus]`, `[Bridge]`, and `[Pre-Chorus]` are supported.
- Blank lines are ignored.

## Usage

Desktop GUI:

```powershell
.\run_generate_lyrics_gui.bat
```

The GUI lets you:

- paste lyrics directly for `1st Song` through `4th Song`
- set the order of songs
- type a title for each song
- load up to 4 sample songs from `txt-lyrics` for quick testing
- review the auto-split draft and edit `---` slide breaks before export
- preview validation before generating
- create one PPT from exactly `3` or `4` songs

CLI from text files:

Run a dry analysis first:

```powershell
python .\generate_lyrics_ppt.py --dry-run
```

Generate decks with 4 songs per PPT:

```powershell
python .\generate_lyrics_ppt.py --songs-per-ppt 4
```

Generate decks with 3 songs per PPT and keep the sample `WELCOME` slide:

```powershell
python .\generate_lyrics_ppt.py --songs-per-ppt 3 --include-welcome-slide
```

Use a specific sample PPT:

```powershell
python .\generate_lyrics_ppt.py --template .\samples-ppt\March-21-2026.pptx
```

## Output Rules

- One title slide per song
- Lyric slides usually contain `2` to `3` lines
- Very short lines may be grouped into `4` lines
- Chorus and bridge slides keep a small section cue in the upper-left
- Output files are written to `generated-ppt`

## Requirements

- Windows
- Python
- Microsoft PowerPoint installed
- `pywin32`

Install dependency:

```powershell
pip install pywin32
```

## Important Assumption

The generator duplicates a title-slide prototype and a lyric-slide prototype from the sample PPT. That means all sample decks should follow the same layout family, which matches the samples currently in `samples-ppt`.
