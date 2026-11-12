from taskiq_redis import RedisStreamBroker, RedisAsyncResultBackend
from taskiq import SmartRetryMiddleware

from app.config import BROKER_URL

# хранилище результатов TaskIQ
result_backend = RedisAsyncResultBackend(redis_url=BROKER_URL)

# брокер с Redis Stream + Retry
broker = (
    RedisStreamBroker(url=BROKER_URL)
    .with_result_backend(result_backend)
    .with_middlewares(
        SmartRetryMiddleware(
            default_retry_count=3,
            default_delay=5,
        )
    )
)