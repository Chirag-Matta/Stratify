import json
import os
import sys
from dotenv import load_dotenv
load_dotenv()

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from confluent_kafka import Consumer
from db.models import create_tables
from services.segment_svc import SegmentService

SessionLocal = create_tables(os.getenv("DATABASE_URL"))

def main():
    c = Consumer({
        'bootstrap.servers': os.getenv("KAFKA_SERVERS", "localhost:9092"),
        'group.id': 'segmentation-group-v3',
        'auto.offset.reset': 'earliest'
    })

    c.subscribe(['order_placed'])
    print("[Consumer] Listening for order_placed events...")

    while True:
        msg = c.poll(1.0)

        if msg is None:
            continue
        if msg.error():
            print(f"[Consumer] Error: {msg.error()}")
            continue

        event = json.loads(msg.value().decode('utf-8'))
        user_id = event.get("user_id")

        if not user_id:
            print("[Consumer] Skipping, no user_id")
            continue

        print(f"[Consumer] Received order_placed for user: {user_id}")

        db = SessionLocal()
        try:
            service = SegmentService(db)
            matched_segments = service.refresh_user_segments(user_id)
            print(f"[Consumer] User {user_id} now in segments: {matched_segments}")
        except Exception as e:
            print(f"[Consumer] Error: {e}")
        finally:
            db.close()

if __name__ == "__main__":
    main()