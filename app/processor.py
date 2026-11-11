from pydantic import ValidationError
import json

from app import storage
from app.schemas.order import SUPPORTED_CURRENCIES, Order
from app.services.rates import get_rate_to_usd
from app.summary import build_summary


def _updater(job_id: str, processed: int, errors: list[dict]) -> None:
    storage.update_job(
        job_id,
        processed=processed,
        failed=len(errors)
    )

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

    errors: list[dict] = []
    processed_orders: list[dict] = []
    processed = 0
    seen_order_ids: set[int] = set() 

    for raw in raw_orders:
        order_id = raw.get("order_id") if isinstance(raw, dict) else None
        # валидация
        try:
            order = Order.model_validate(raw)
        except ValidationError as exc:
            errors.append(
                {
                    "order_id": order_id,
                    "reason": exc.errors()[0]["msg"],
                }
            )
            _updater(job_id, processed, errors)
            continue

        # неизвестная валюта
        if order.currency not in SUPPORTED_CURRENCIES:
            errors.append(
                {
                    "order_id": order_id,
                    "reason": f"unknown currency {order.currency}"
                }
            )
            _updater(job_id, processed, errors)
            continue
        
        # дубликат
        if order_id in seen_order_ids:
            errors.append(
                {
                    "order_id": order_id,
                    "reason": f"duplicate order"
                }
            )
            _updater(job_id, processed, errors)
            continue

        # перевод в usd
        try:
            rate = get_rate_to_usd(order.currency, order.order_date.isoformat())
        except Exception as exc:
            errors.append(
                {
                    "order_id": order_id,
                    "reason": str(exc)
                }
            )
            _updater(job_id, processed, errors)
            continue
        amount_usd = round(order.amount * rate, 2)
        # print(rate)

        seen_order_ids.add(order_id)
        processed += 1
        processed_orders.append(
            {
                "order_id": order_id,
                "customer": order.customer,
                "product": order.product,
                "amount": order.amount,
                "currency": order.currency,
                "order_date": order.order_date.isoformat(),
                "amount_usd": amount_usd,
            }
        )
        _updater(job_id, processed, errors)

    # print("PROCESSED_ORDERS:", processed_orders)
    summary = build_summary(processed_orders)
    storage.update_job(
        job_id,
        status="done",
        processed_orders=processed_orders,
        result={
            "job_id": job_id,
            "status": "done",
            "total": total,
            "processed": processed,
            "failed": len(errors),
            "summary": summary,
            "errors": errors,
        },
    )