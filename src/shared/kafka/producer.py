import json
from aiokafka import AIOKafkaProducer


def create_producer():
    return AIOKafkaProducer(
        bootstrap_servers="kafka:9092",
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        retries=10,
        retry_backoff_ms=500,
        request_timeout_ms=1000,
        acks="all",
    )
