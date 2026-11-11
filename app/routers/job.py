from fastapi import APIRouter, HTTPException, UploadFile, Response
from app.storage import redis
from app.tasks.processor import process_orders
from app.schemas.job import JobCreated, JobResult, JobStatus

from typing import Literal
import uuid
import csv
import io

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("", status_code=202, response_model=JobCreated)
async def create_job(file: UploadFile):
    job_id = str(uuid.uuid4())
    redis.create_job(job_id)
    content = await file.read()

    # задача app.processor:process_orders с job_id, content -> в очередь TaskIQ (в Redis-брокер)
    await process_orders.kiq(job_id, content)
    
    return JobCreated(job_id=job_id)


@router.get("/{job_id}", response_model=JobStatus)
def get_status(job_id: str):
    job = redis.get_job(job_id)
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
    job = redis.get_job(job_id)
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