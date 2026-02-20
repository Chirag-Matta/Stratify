# services/kafka_producer.py

import json
import os
from kafka import KafkaProducer
from kafka.errors import KafkaError

producer = None

def get_producer():
    global producer
    if producer is None:
        producer = KafkaProducer(
            bootstrap_servers=os.getenv("KAFKA_SERVERS", "localhost:9092"),
            value_serializer=lambda v: json.dumps(v).encode("utf-8")
        )
    return producer

def publish_event(topic: str, payload: dict):
    future = get_producer().send(topic, payload)
    try:
        record_metadata = future.get(timeout=10)  # blocks and waits for ack
        print(f"[Kafka] Delivered to topic={record_metadata.topic} partition={record_metadata.partition} offset={record_metadata.offset}")
    except KafkaError as e:
        print(f"[Kafka] FAILED to deliver message: {e}")