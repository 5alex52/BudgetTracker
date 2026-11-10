import redis
from celery import Celery
from celery import shared_task

from .config import settings
from .constants import TIMEOUT_REDIS

celery_app = Celery(
    "tasks",
    broker=f"pyamqp://{settings.RABBIT_USER}:{settings.RABBIT_PASSWORD}@{settings.RABBIT_HOST}:{settings.RABBIT_PORT}//",
    backend="rpc://",
)

redis_client = redis.StrictRedis(
    host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=0
)
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
)
