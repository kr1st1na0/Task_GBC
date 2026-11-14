from pydantic import ValidationError
import json
import asyncio

from app.storage import redis
from app.schemas.order import SUPPORTED_CURRENCIES, Order
from app.services.rates import get_rate_to_usd
from app.tasks.summary import build_summary
from app.tasks.broker import broker


async def _updater(job_id: str, processed: int, errors: list[dict], processed_orders: list[dict], all_seen_ids: set[int]) -> None:
    await redis.update_job(
        job_id,
        processed=processed,
        failed=len(errors),
        processed_orders=processed_orders,
        all_seen_ids=list(all_seen_ids),
        result={"errors": errors},
    )

@broker.task(retry_on_error=True, max_retries=3)
async def process_orders(job_id: str, content: bytes) -> None:
    job = await redis.get_job(job_id)
    if job is None or job["status"] == "done":
        return

    # берем job из прошлого запуска (retry) или пустота
    result = job.get("result") or {}
    errors = result.get("errors", [])
    processed_orders = job.get("processed_orders", [])
    processed = job.get("processed", 0)
    all_seen_ids = set(job.get("all_seen_ids", []))
    #

    try:
        raw_orders = json.loads(content)
    except json.JSONDecodeError as exc:
        await redis.update_job(
            job_id,
            status="failed",
            result={"error": f"invalid json: {exc}"},
        )
        return

    total = len(raw_orders)
    await redis.update_job(
        job_id,
        status="running",
        total=total)
    local_seen_ids: set[int] = set() # при текущем запуске для дубликатов

    for raw in raw_orders:
    #! чекали retry и дубликаты
    # initial_processed_count = len(processed_orders)
    # for i, raw in enumerate(raw_orders):
    #     if i == 2 and initial_processed_count == 0:  #! перед 3-й записью при 1-м запуске падаем
    #         raise Exception("test fall: check retry")
    #!
        order_id = raw.get("order_id") if isinstance(raw, dict) else None

        # дубликат текущий запуск
        if order_id in local_seen_ids: # если уже при текущем запуске был
            errors.append(
                {
                    "order_id": order_id,
                    "reason": f"duplicate order"
                }
            )
            all_seen_ids.add(order_id)
            await _updater(job_id, processed, errors, processed_orders, all_seen_ids)
            continue
        # не считаем дубликатом то, что обработали в прошлом запуске
        if order_id in all_seen_ids: # из прошлого запуска (retry)
            local_seen_ids.add(order_id)
            continue

        local_seen_ids.add(order_id)
        
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
            all_seen_ids.add(order_id)
            await _updater(job_id, processed, errors, processed_orders, all_seen_ids)
            continue

        # неизвестная валюта
        if order.currency not in SUPPORTED_CURRENCIES:
            errors.append(
                {
                    "order_id": order_id,
                    "reason": f"unknown currency: {order.currency}"
                }
            )
            all_seen_ids.add(order_id)
            await _updater(job_id, processed, errors, processed_orders, all_seen_ids)
            continue

        # перевод в usd
        try:
            rate = await get_rate_to_usd(order.currency, order.order_date.isoformat())
        except Exception as exc:
            errors.append(
                {
                    "order_id": order_id,
                    "reason": str(exc)
                }
            )
            all_seen_ids.add(order_id)
            await _updater(job_id, processed, errors, processed_orders, all_seen_ids)
            continue
        amount_usd = round(order.amount * rate, 2)

        # print(rate)
        all_seen_ids.add(order_id)
        processed += 1
        processed_orders.append(
            {
                "order_id": order_id,
                "customer": order.customer,
                "product": order.product,
                "amount": order.amount,
                "currency": order.currency,
                "order_date": order.order_date.isoformat(),
                "review": order.review,
                "amount_usd": amount_usd,
            }
        )
        await _updater(job_id, processed, errors, processed_orders, all_seen_ids)

    # print("PROCESSED_ORDERS:", processed_orders)
    await finalize_job.kiq(job_id) # все сломало.

@broker.task(retry_on_error=True, max_retries=3)
async def finalize_job(job_id: str) -> None:
    job = await redis.get_job(job_id)
    if job is None or job["status"] == "done":
        return

    processed_orders = job.get("processed_orders", [])
    result = job.get("result") or {}
    errors = result.get("errors", [])
    processed = job.get("processed", 0)
    total = job.get("total", 0)
    all_seen_ids = job.get("all_seen_ids", [])

    # summary = build_summary(processed_orders)
    # чтоб пандас не блокал even loop, отправляем его в отдельный поток
    # при мелких нагрузках мб дольше, но хззз (тк надо переключить, дождаться, вернуть результат)
    summary = await asyncio.to_thread(build_summary, processed_orders)

    await redis.update_job(
        job_id,
        status="done",
        processed_orders=processed_orders,
        all_seen_ids=all_seen_ids,
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