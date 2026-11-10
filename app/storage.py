from typing import Any

# костыль костыль, будет Redis/PosgreSQL
_jobs: dict[str, dict[str, Any]] = {}


def create_job(job_id: str) -> None:
    _jobs[job_id] = {
        "status": "pending",
        "total": 0,
        "processed": 0,
        "failed": 0,
        "processed_orders": [],
        "result": None,
    }


def get_job(job_id: str) -> dict[str, Any] | None:
    return _jobs.get(job_id)


def update_job(job_id: str, **fields: Any) -> None:
    if job_id in _jobs:
        _jobs[job_id].update(fields)