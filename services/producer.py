import json
import os
from confluent_kafka import Producer
from dotenv import load_dotenv
load_dotenv()

producer = None

def get_producer():
    global producer
    if producer is None:
        producer = Producer({
            'bootstrap.servers': os.getenv("KAFKA_SERVERS", "localhost:9092")
        })
    return producer

def publish_event(topic: str, payload: dict):
    def delivery_report(err, msg):
        if err:
            print(f"[Kafka] FAILED: {err}")
        else:
            print(f"[Kafka] Delivered to topic={msg.topic()} partition={msg.partition()} offset={msg.offset()}")

    get_producer().produce(topic, json.dumps(payload).encode('utf-8'), callback=delivery_report)
    get_producer().flush()