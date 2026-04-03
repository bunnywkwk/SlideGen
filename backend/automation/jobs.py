from dataclasses import dataclass, field
from pathlib import Path
from threading import Lock, Thread
from time import time
from typing import Any
from uuid import uuid4


@dataclass
class JobRecord:
    job_id: str
    job_type: str
    operation: str
    status: str = "queued"
    progress: int = 0
    message: str = "Queued..."
    result_payload: dict[str, Any] | None = None
    output_path: Path | None = None
    error: str | None = None
    created_at: float = field(default_factory=time)


class JobStore:
    def __init__(self) -> None:
        self._jobs: dict[str, JobRecord] = {}
        self._lock = Lock()

    def create_job(self, job_type: str, operation: str, message: str) -> JobRecord:
        record = JobRecord(
            job_id=uuid4().hex,
            job_type=job_type,
            operation=operation,
            progress=4,
            message=message,
        )
        with self._lock:
            self._jobs[record.job_id] = record
        return record

    def update(self, job_id: str, progress: int, message: str, status: str = "running") -> None:
        with self._lock:
            record = self._jobs[job_id]
            record.status = status
            record.progress = max(0, min(100, int(progress)))
            record.message = message

    def complete_preview(self, job_id: str, payload: dict[str, Any], message: str = "Preview ready.") -> None:
        with self._lock:
            record = self._jobs[job_id]
            record.status = "completed"
            record.progress = 100
            record.message = message
            record.result_payload = payload

    def complete_file(self, job_id: str, output_path: Path, message: str = "File ready.") -> None:
        with self._lock:
            record = self._jobs[job_id]
            record.status = "completed"
            record.progress = 100
            record.message = message
            record.output_path = output_path

    def fail(self, job_id: str, error: str) -> None:
        with self._lock:
            record = self._jobs[job_id]
            record.status = "failed"
            record.message = "Request failed."
            record.error = error

    def get(self, job_id: str) -> JobRecord | None:
        with self._lock:
            return self._jobs.get(job_id)

    def consume_output(self, job_id: str) -> Path | None:
        with self._lock:
            record = self._jobs.get(job_id)
            if record is None:
                return None
            output_path = record.output_path
            record.output_path = None
            return output_path


job_store = JobStore()


def run_job_in_thread(worker) -> None:
    Thread(target=worker, daemon=True).start()
