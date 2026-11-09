from pydantic import ValidationError
import json

from app import storage
from app.schemas.order import Order

# ! костыль пока костыль...
def process_orders(job_id: str, content: bytes) -> None:
    storage.update_job(job_id, status="running")

    try:
        raw_orders = json.loads(content)
    except json.JSONDecodeError as exc:
        storage.update_job(
            job_id,
            status="failed",
            result={"error": f"invalid json: {exc}"},
        )
        return

    total = len(raw_orders)
    storage.update_job(job_id, total=total)

    processed = 0
    errors: list[dict] = []

    for raw in raw_orders:
        try:
            Order.model_validate(raw)
            processed += 1
        except ValidationError as exc:
            errors.append(
                {
                    "order_id": raw.get("order_id") if isinstance(raw, dict) else None,
                    "reason": exc.errors()[0]["msg"],
                }
            )

        storage.update_job(
            job_id,
            processed=processed,
            failed=len(errors),
        )

    storage.update_job(
        job_id,
        status="done",
        result={
            "job_id": job_id,
            "status": "done",
            "total": total,
            "processed": processed,
            "failed": len(errors),
            "summary": {},          #!!!
            "errors": errors,
        },
    )