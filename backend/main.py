import json
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi import File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask

from automation.constants import BACKEND_OUTPUT_DIR, BACKEND_UPLOAD_DIR, BOOK_OPTIONS
from automation.jobs import job_store, run_job_in_thread
from automation.lyrics_service import build_lyrics_preview, generate_lyrics_ppt
from automation.rate_limits import WeeklyLimitExceeded, weekly_export_limiter
from automation.schemas import (
    AppInfo,
    DefaultsResponse,
    GenerateResponse,
    GenerateRequest,
    JobAcceptedResponse,
    JobStatusResponse,
    OptionsResponse,
    VersesGenerateRequest,
)
from automation.settings import load_settings
from automation.verses_service import build_verses_preview, generate_verses_ppt

settings = load_settings()

app = FastAPI(
    title=settings.app_name,
    description="Deployable FastAPI backend for lyrics and verse slide generation.",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _raise_http_error(exc: Exception) -> None:
    if isinstance(exc, FileNotFoundError):
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if isinstance(exc, ValueError):
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if isinstance(exc, WeeklyLimitExceeded):
        raise HTTPException(
            status_code=429,
            detail=f"You have reached the weekly PowerPoint export limit of {exc.limit}. Try again next week.",
        ) from exc
    raise HTTPException(status_code=500, detail=str(exc)) from exc


async def _save_upload_file(upload: UploadFile) -> Path:
    BACKEND_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    suffix = Path(upload.filename or "").suffix.lower()
    file_path = BACKEND_UPLOAD_DIR / f"{uuid4().hex}{suffix}"
    size = 0
    with file_path.open("wb") as file_handle:
        while True:
            chunk = upload.file.read(1024 * 1024)
            if not chunk:
                break
            size += len(chunk)
            if size > settings.max_upload_size_bytes:
                file_handle.close()
                file_path.unlink(missing_ok=True)
                raise HTTPException(
                    status_code=413,
                    detail=(
                        "Uploaded background image is too large. "
                        f"Use an image smaller than {settings.max_upload_size_bytes // (1024 * 1024)} MB."
                    ),
                )
            file_handle.write(chunk)
    return file_path


def _cleanup_temp_file(path: Path) -> None:
    if path.exists():
        path.unlink(missing_ok=True)


def _cleanup_files(*paths: Path | None) -> None:
    for path in paths:
        if path is not None:
            _cleanup_temp_file(path)


def _cleanup_job_output(job_id: str, output_path: Path) -> None:
    _cleanup_temp_file(output_path)
    job_store.consume_output(job_id)


def _job_error_message(exc: Exception) -> str:
    if isinstance(exc, (FileNotFoundError, ValueError, HTTPException)):
        return str(getattr(exc, "detail", exc))
    return str(exc) or "Unexpected server error."


def _build_job_status_response(job_id: str) -> JobStatusResponse:
    record = job_store.get(job_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Job not found.")

    return JobStatusResponse(
        job_id=record.job_id,
        job_type=record.job_type,
        operation=record.operation,
        status=record.status,
        progress=record.progress,
        message=record.message,
        result=GenerateResponse.model_validate(record.result_payload) if record.result_payload else None,
        download_ready=record.output_path is not None and record.status == "completed",
        download_url=f"/jobs/{record.job_id}/download" if record.output_path is not None and record.status == "completed" else None,
        error=record.error,
    )


def _get_client_identifier(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for", "").strip()
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def _consume_export_quota(request: Request) -> None:
    weekly_export_limiter.consume(
        client_id=_get_client_identifier(request),
        limit=settings.weekly_ppt_limit,
    )


@app.get("/")
def health_check() -> dict[str, str]:
    return {
        "status": "ok",
        "message": f"{settings.app_name} is running.",
    }


@app.get("/health")
def health_details() -> dict[str, str]:
    return {
        "status": "ok",
        "engine": settings.ppt_engine,
        "verse_lookup_ready": str(bool(settings.youversion_api_key or settings.allow_public_api_keys)).lower(),
    }


@app.get("/options", response_model=OptionsResponse)
def get_options() -> OptionsResponse:
    return OptionsResponse(
        books=BOOK_OPTIONS,
        bible_versions=settings.version_options,
        defaults=DefaultsResponse(
            left_version=settings.default_left_version,
            right_version=settings.default_right_version,
            lyrics_song_slots=settings.default_lyrics_song_slots,
        ),
        app=AppInfo(
            name=settings.app_name,
            ppt_engine=settings.ppt_engine,
            verse_lookup_ready=bool(settings.youversion_api_key or settings.allow_public_api_keys),
            allow_public_api_keys=settings.allow_public_api_keys,
        ),
        output_directory="Temporary download storage",
    )


@app.post("/generate", response_model=GenerateResponse)
def generate_preview(request: GenerateRequest) -> GenerateResponse:
    try:
        if request.job_type == "lyrics":
            # Lyrics preview stays fully local and uses your existing parsing/validation logic.
            preview = build_lyrics_preview(request)
            return GenerateResponse(
                job_type="lyrics",
                message="Lyrics preview generated successfully.",
                lyrics_preview=preview,
            )

        # Verse preview fetches the text first, then returns a browser-friendly JSON response.
        preview = build_verses_preview(request)
        return GenerateResponse(
            job_type="verses",
            message="Verses preview generated successfully.",
            verses_preview=preview,
        )
    except Exception as exc:
        _raise_http_error(exc)


@app.post("/jobs/preview", response_model=JobAcceptedResponse)
def queue_preview_job(request: GenerateRequest) -> JobAcceptedResponse:
    record = job_store.create_job(request.job_type, "preview", "Queued preview request...")

    def worker() -> None:
        try:
            job_store.update(record.job_id, 6, "Starting preview job...")
            if request.job_type == "lyrics":
                preview = build_lyrics_preview(
                    request,
                    progress_callback=lambda progress, message: job_store.update(record.job_id, progress, message),
                )
                payload = GenerateResponse(
                    job_type="lyrics",
                    message="Lyrics preview generated successfully.",
                    lyrics_preview=preview,
                ).model_dump(mode="json")
            else:
                preview = build_verses_preview(
                    request,
                    progress_callback=lambda progress, message: job_store.update(record.job_id, progress, message),
                )
                payload = GenerateResponse(
                    job_type="verses",
                    message="Verses preview generated successfully.",
                    verses_preview=preview,
                ).model_dump(mode="json")
            job_store.complete_preview(record.job_id, payload)
        except Exception as exc:
            job_store.fail(record.job_id, _job_error_message(exc))

    run_job_in_thread(worker)

    return JobAcceptedResponse(
        job_id=record.job_id,
        job_type=record.job_type,
        operation=record.operation,
        status=record.status,
        progress=record.progress,
        message=record.message,
    )


@app.post("/generate-ppt")
def generate_ppt(request: GenerateRequest, http_request: Request) -> FileResponse:
    try:
        _consume_export_quota(http_request)
        if request.job_type == "lyrics":
            output_path = generate_lyrics_ppt(request)
        else:
            output_path = generate_verses_ppt(request)

        return FileResponse(
            path=output_path,
            media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
            filename=output_path.name,
            background=BackgroundTask(_cleanup_files, output_path),
        )
    except Exception as exc:
        _raise_http_error(exc)


@app.post("/jobs/ppt", response_model=JobAcceptedResponse)
def queue_ppt_job(request: GenerateRequest, http_request: Request) -> JobAcceptedResponse:
    try:
        _consume_export_quota(http_request)
    except Exception as exc:
        _raise_http_error(exc)

    record = job_store.create_job(request.job_type, "ppt", "Queued PowerPoint export...")

    def worker() -> None:
        try:
            job_store.update(record.job_id, 6, "Starting export job...")
            if request.job_type == "lyrics":
                output_path = generate_lyrics_ppt(
                    request,
                    progress_callback=lambda progress, message: job_store.update(record.job_id, progress, message),
                )
            else:
                output_path = generate_verses_ppt(
                    request,
                    progress_callback=lambda progress, message: job_store.update(record.job_id, progress, message),
                )
            job_store.complete_file(record.job_id, output_path)
        except Exception as exc:
            job_store.fail(record.job_id, _job_error_message(exc))

    run_job_in_thread(worker)

    return JobAcceptedResponse(
        job_id=record.job_id,
        job_type=record.job_type,
        operation=record.operation,
        status=record.status,
        progress=record.progress,
        message=record.message,
    )


@app.post("/verses/generate-ppt")
async def generate_verses_ppt_with_style(
    http_request: Request,
    payload: str = Form(...),
    style_file: UploadFile | None = File(default=None),
) -> FileResponse:
    temp_file_path: Path | None = None

    try:
        payload_data = json.loads(payload)
        request = VersesGenerateRequest.model_validate(payload_data)

        if style_file is not None and style_file.filename:
            temp_file_path = await _save_upload_file(style_file)
            suffix = temp_file_path.suffix.lower()

            if suffix in {".png", ".jpg", ".jpeg", ".webp"}:
                request = request.model_copy(update={"background_image_path": str(temp_file_path)})
            else:
                raise HTTPException(status_code=400, detail="Unsupported style file. Please upload a background image.")

        _consume_export_quota(http_request)
        output_path = generate_verses_ppt(request)
        return FileResponse(
            path=output_path,
            media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
            filename=output_path.name,
            background=BackgroundTask(_cleanup_files, output_path, temp_file_path),
        )
    except HTTPException:
        if temp_file_path is not None:
            _cleanup_temp_file(temp_file_path)
        raise
    except Exception as exc:
        if temp_file_path is not None:
            _cleanup_temp_file(temp_file_path)
        _raise_http_error(exc)


@app.post("/jobs/verses-ppt", response_model=JobAcceptedResponse)
async def queue_verse_ppt_job(
    http_request: Request,
    payload: str = Form(...),
    style_file: UploadFile | None = File(default=None),
) -> JobAcceptedResponse:
    temp_file_path: Path | None = None

    try:
        payload_data = json.loads(payload)
        request = VersesGenerateRequest.model_validate(payload_data)

        if style_file is not None and style_file.filename:
            temp_file_path = await _save_upload_file(style_file)
            suffix = temp_file_path.suffix.lower()

            if suffix in {".png", ".jpg", ".jpeg", ".webp"}:
                request = request.model_copy(update={"background_image_path": str(temp_file_path)})
            else:
                raise HTTPException(status_code=400, detail="Unsupported style file. Please upload a background image.")

        _consume_export_quota(http_request)
        record = job_store.create_job("verses", "ppt", "Queued verse PowerPoint export...")

        def worker() -> None:
            try:
                job_store.update(record.job_id, 6, "Starting verse export...")
                output_path = generate_verses_ppt(
                    request,
                    progress_callback=lambda progress, message: job_store.update(record.job_id, progress, message),
                )
                job_store.complete_file(record.job_id, output_path)
            except Exception as exc:
                job_store.fail(record.job_id, _job_error_message(exc))
            finally:
                if temp_file_path is not None:
                    _cleanup_temp_file(temp_file_path)

        run_job_in_thread(worker)

        return JobAcceptedResponse(
            job_id=record.job_id,
            job_type=record.job_type,
            operation=record.operation,
            status=record.status,
            progress=record.progress,
            message=record.message,
        )
    except HTTPException:
        if temp_file_path is not None:
            _cleanup_temp_file(temp_file_path)
        raise
    except Exception as exc:
        if temp_file_path is not None:
            _cleanup_temp_file(temp_file_path)
        _raise_http_error(exc)


@app.get("/jobs/{job_id}", response_model=JobStatusResponse)
def get_job_status(job_id: str) -> JobStatusResponse:
    return _build_job_status_response(job_id)


@app.get("/jobs/{job_id}/download")
def download_job_file(job_id: str) -> FileResponse:
    record = job_store.get(job_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Job not found.")
    if record.output_path is None or record.status != "completed":
        raise HTTPException(status_code=409, detail="This file is not ready to download yet.")

    return FileResponse(
        path=record.output_path,
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        filename=record.output_path.name,
        background=BackgroundTask(_cleanup_job_output, job_id, record.output_path),
    )
