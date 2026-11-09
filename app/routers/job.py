from fastapi import APIRouter, BackgroundTasks, HTTPException, UploadFile
from fastapi import status as http_status
from app import processor, storage
from app.schemas.job import JobCreated, JobResult, JobStatus
import uuid

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


@router.get("/{job_id}/result", response_model=JobResult)
def get_result(job_id: str):
    job = storage.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    if job["status"] != "done":
        raise HTTPException(
            status_code=409,
            detail=f"job is not finished, status={job['status']}",
        )
    return JobResult(**job["result"])