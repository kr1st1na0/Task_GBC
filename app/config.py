import os

REDIS_URL = os.getenv("REDIS_URL")
if not REDIS_URL:
    raise RuntimeError("REDIS_URL is not set (.env file)")

BROKER_URL = os.getenv("BROKER_URL")
if not BROKER_URL:
    raise RuntimeError("BROKER_URL is not set (.env file)")