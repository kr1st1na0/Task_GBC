from fastapi import APIRouter, BackgroundTasks, HTTPException, UploadFile, Response
from app import processor, storage
from app.schemas.job import JobCreated, JobResult, JobStatus

from typing import Literal
import uuid
import csv
import io

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("", status_code=202, response_model=JobCreated)
async def create_job(file: UploadFile, background_tasks: BackgroundTasks):
    job_id = str(uuid.uuid4())
    storage.create_job(job_id)
    content = await file.read()
    background_tasks.add_task(processor.process_orders, job_id, content)
    return JobCreated(job_id=job_id)


@router.get("/{job_id}", response_model=JobStatus)
def get_status(job_id: str):
    job = storage.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    return JobStatus(
        job_id=job_id,
        status=job["status"],
        total=job["total"],
        processed=job["processed"],
        failed=job["failed"],
    )


@router.get("/{job_id}/result")
def get_result(job_id: str, format: Literal["json", "csv"] = "json"):
    job = storage.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    if job["status"] != "done":
        raise HTTPException(
            status_code=409,
            detail=f"job is not finished, status={job['status']}",
        )
    if format == "csv":
        return _result_csv_format(job_id, job)
    return JobResult(**job["result"])


def _result_csv_format(job_id: str, job: dict) -> Response:
    rows = job.get("processed_orders", [])

    buf = io.StringIO() # буфер-файл в оперативке, сам уберется...
    if rows:
        writer = csv.DictWriter(buf, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    content = buf.getvalue()

    return Response(
        content=content,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{job_id}.csv"'},
    )