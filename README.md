# SlideGen

SlideGen is a full-stack web app for generating church lyric slides and Bible verse slides as PowerPoint files.

It now has two goals:

- stay useful locally for your current workflow
- be structured so it can be deployed for other users

## What Changed

The old desktop generators are still included in:

- `lyrics-generator/`
- `verse-generator/`

The web app has been refactored so the backend no longer depends on Windows-only PowerPoint automation for its default path.

That means:

- lyrics parsing is now handled by pure Python backend modules
- Bible lookup is now handled by pure Python backend modules
- PowerPoint generation now defaults to a portable `python-pptx` engine
- the old `pywin32` PowerPoint automation is kept only as an optional legacy mode
- the frontend UI is simplified so normal users do not need to see template paths or API-key fields

## Architecture

```text
SlideGen/
  backend/
    main.py
    requirements.txt
    requirements-legacy-windows.txt
    .env.example
    output/
    automation/
      __init__.py
      bible_client.py
      constants.py
      legacy_loader.py
      lyrics_domain.py
      lyrics_service.py
      presentation_legacy.py
      presentation_portable.py
      schemas.py
      settings.py
      verses_service.py
  frontend/
    .env.example
    index.html
    package.json
    vite.config.js
    src/
      App.jsx
      index.css
      main.jsx
      components/
      lib/
      pages/
  lyrics-generator/
  verse-generator/
  README.md
```

## Main Modules

### Lyrics Module

Used for:

- pasting 1 to 4 songs
- validating lyric formatting
- generating clean lyric slide chunks
- exporting a `.pptx`

### Verses Module

Used for:

- selecting book and chapter
- selecting verse range
- choosing two Bible versions
- previewing matched verses
- exporting a `.pptx`

## Backend Design

### `backend/main.py`

FastAPI entry point.

Routes:

- `GET /`
- `GET /health`
- `GET /options`
- `POST /generate`
- `POST /generate-ppt`

### `backend/automation/lyrics_domain.py`

Pure lyrics domain logic:

- parse songs
- validate songs
- split songs into slide chunks
- build draft text

This file is deployable because it does not import `pywin32`.

### `backend/automation/bible_client.py`

Pure YouVersion API integration:

- find Bible versions
- resolve books
- fetch verses

### `backend/automation/presentation_portable.py`

Default PowerPoint generator.

Uses `python-pptx`, so it works without Microsoft PowerPoint installed.

This is the engine intended for deployment.

### `backend/automation/presentation_legacy.py`

Optional Windows-only fallback that calls the original PowerPoint automation.

Use this only if you still want to preserve the exact legacy PowerPoint-template workflow on Windows.

### `backend/automation/settings.py`

Loads environment variables for:

- app name
- CORS origins
- PowerPoint engine mode
- YouVersion API key
- default Bible versions
- upload size limit
- weekly PPT export limit

## Frontend Design

The frontend uses React + Vite and is organized into separate pages:

- `/` overview
- `/lyrics` lyrics generator
- `/verses` verses generator

The UI is intentionally simplified for end users:

- no template path inputs in the normal flow
- no public API key field unless you later decide to support that
- only the inputs the user actually needs

## Environment Variables

Create a backend environment file or set these in your hosting platform:

```text
SLIDEGEN_APP_NAME=SlideGen API
SLIDEGEN_CORS_ORIGINS=https://your-frontend-domain.vercel.app
SLIDEGEN_PPT_ENGINE=portable
SLIDEGEN_ENABLE_LEGACY_TEMPLATES=false
SLIDEGEN_ALLOW_PUBLIC_API_KEYS=false
SLIDEGEN_YOUVERSION_API_KEY=your_key_here
SLIDEGEN_DEFAULT_LEFT_VERSION=NIV11
SLIDEGEN_DEFAULT_RIGHT_VERSION=APD
SLIDEGEN_DEFAULT_LANGUAGE_RANGES=*
SLIDEGEN_DEFAULT_LYRICS_SONG_SLOTS=4
SLIDEGEN_VERSION_OPTIONS=NIV11,NKJV,ESV,NLT,KJV,AMP,APD,MBBTAG
SLIDEGEN_MAX_UPLOAD_SIZE_BYTES=8388608
SLIDEGEN_WEEKLY_PPT_LIMIT=2
```

Recommended production defaults:

- keep `SLIDEGEN_ALLOW_PUBLIC_API_KEYS=false`
- set `SLIDEGEN_CORS_ORIGINS` to your real frontend URL, not `*`
- keep `SLIDEGEN_MAX_UPLOAD_SIZE_BYTES=8388608` unless you truly need larger backgrounds
- keep `SLIDEGEN_WEEKLY_PPT_LIMIT=2` while you are on a free plan

## Install

### Backend

```powershell
cd c:\Users\AERON\sideprojects\SlideGen
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r .\backend\requirements.txt
```

### Frontend

```powershell
cd c:\Users\AERON\sideprojects\SlideGen\frontend
npm install
```

## Run In Development

### Terminal 1

```powershell
cd c:\Users\AERON\sideprojects\SlideGen
.venv\Scripts\Activate.ps1
cd backend
uvicorn main:app --reload
```

### Terminal 2

```powershell
cd c:\Users\AERON\sideprojects\SlideGen\frontend
npm run dev
```

Open:

- `http://127.0.0.1:5173`
- `http://127.0.0.1:8000/docs`

## Deployment Notes

The default web app path is now much closer to deployable because it uses:

- FastAPI
- React + Vite
- `python-pptx`
- environment-based server configuration

### Best production setup

- keep the YouVersion API key on the backend only
- deploy the FastAPI backend separately from the frontend or behind one domain
- build the frontend with `npm run build`
- serve the Vite output from static hosting or a reverse proxy
- generated PPT files are temporary and are deleted after download
- uploaded background images are size-limited and temporary
- public users are limited to `2` PPT exports per week per IP by default

### Files added for production

- `.gitignore`
- `.dockerignore`
- `Dockerfile`
- `frontend/vercel.json`

These files help you:

- avoid committing secrets and local build folders
- package the backend for a Linux host
- deploy the React app as a single-page app on Vercel

## Recommended Free Deployment

Recommended stack:

- frontend: Vercel
- backend: Koyeb

Why this split:

- Vite builds into static files that Vercel handles very well
- your FastAPI backend needs a long-running server, file generation, and environment variables
- the backend is better hosted as a containerized service than as a serverless function

## Production Checklist

Before you deploy:

1. Make sure your real `.env` files are not committed.
2. Rotate your YouVersion API key if it was ever exposed publicly.
3. Confirm local test flow still works:
   - lyrics preview
   - verses preview
   - PPT export
4. Commit the deployment files.

## Deploy Frontend On Vercel

1. Push the project to GitHub.
2. In Vercel, import the repo.
3. Set the project root to `frontend`.
4. Keep the default Vite build settings:
   - build command: `npm run build`
   - output directory: `dist`
5. Add this environment variable in Vercel after your backend exists:

```text
VITE_API_BASE_URL=https://your-backend-domain.example.com
```

6. Redeploy after setting the variable.

`frontend/vercel.json` is included so React Router routes like `/lyrics` and `/verses` work correctly in production.

## Deploy Backend On Koyeb

1. In Koyeb, create a new web service from your GitHub repo.
2. Deploy using the repo `Dockerfile`.
3. Use these environment variables:

```text
SLIDEGEN_APP_NAME=SlideGen API
SLIDEGEN_CORS_ORIGINS=https://your-frontend-domain.vercel.app
SLIDEGEN_PPT_ENGINE=portable
SLIDEGEN_ENABLE_LEGACY_TEMPLATES=false
SLIDEGEN_ALLOW_PUBLIC_API_KEYS=false
SLIDEGEN_YOUVERSION_API_KEY=your_key_here
SLIDEGEN_DEFAULT_LEFT_VERSION=NIV11
SLIDEGEN_DEFAULT_RIGHT_VERSION=APD
SLIDEGEN_DEFAULT_LANGUAGE_RANGES=*
SLIDEGEN_DEFAULT_LYRICS_SONG_SLOTS=3
SLIDEGEN_VERSION_OPTIONS=NIV11,NKJV,ESV,NLT,KJV,AMP,NASB,MSG,APD,MBBTAG,ASND,RCPV
SLIDEGEN_MAX_UPLOAD_SIZE_BYTES=8388608
SLIDEGEN_WEEKLY_PPT_LIMIT=2
```

4. Once Koyeb gives you a public backend URL, copy it into the Vercel frontend env as `VITE_API_BASE_URL`.
5. Redeploy the frontend.

## Suggested First Production Order

1. Create a GitHub repo for `SlideGen`
2. Push the code
3. Deploy backend on Koyeb
4. Copy backend URL
5. Deploy frontend on Vercel
6. Set frontend env to backend URL
7. Set backend CORS to frontend URL
8. Redeploy both once
9. Test `/lyrics`, `/verses`, and PPT download

### Still optional for local Windows use

If you want to keep the old PowerPoint-template automation path on Windows:

```powershell
pip install -r .\backend\requirements-legacy-windows.txt
```

And set:

```text
SLIDEGEN_ENABLE_LEGACY_TEMPLATES=true
```

## Verification

The refactored project has been checked with:

- Python compile step on `backend/`
- Vite production build on `frontend/`

## Original Desktop Files

These are still available if you want to compare behavior or keep using them:

- `lyrics-generator/generate_lyrics_gui.py`
- `verse-generator/generate_verses_gui.py`
