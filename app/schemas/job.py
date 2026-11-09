from pydantic import BaseModel, Field
from typing import Literal


class JobCreated(BaseModel):
    job_id: str


class JobStatus(BaseModel):
    job_id: str
    status: Literal["pending", "running", "done", "failed"]
    total: int = 0
    processed: int = 0
    failed: int = 0


class JobError(BaseModel):
    order_id: int | None = None
    reason: str


class JobResult(BaseModel):
    job_id: str
    status: Literal["done", "failed"]
    total: int
    processed: int
    failed: int
    summary: dict = Field(default_factory=dict)
    errors: list[JobError] = Field(default_factory=list)