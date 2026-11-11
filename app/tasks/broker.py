from taskiq_redis import RedisStreamBroker, RedisAsyncResultBackend

from app.config import BROKER_URL

# хранилище результатов TaskIQ
result_backend = RedisAsyncResultBackend(redis_url=BROKER_URL)

# брокер с Redis Stream
broker = RedisStreamBroker(url=BROKER_URL).with_result_backend(result_backend)