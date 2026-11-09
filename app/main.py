from fastapi import FastAPI
from app.routers.job import router as jobs_router

app = FastAPI(title="Order Processor")
app.include_router(jobs_router)