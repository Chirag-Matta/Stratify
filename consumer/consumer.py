import json
import os
import sys
from dotenv import load_dotenv
load_dotenv()

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))



from kafka import KafkaConsumer
from db.models import create_tables
from services.segment_svc import SegmentService

SessionLocal = create_tables(os.getenv("DATABASE_URL"))

def main():
    consumer = KafkaConsumer(
        "order_placed",
        bootstrap_servers=os.getenv("KAFKA_SERVERS", "localhost:9092"),
        auto_offset_reset="earliest",
        group_id="segmentation-group-v2",   # changed
        value_deserializer=lambda m: json.loads(m.decode("utf-8"))
    )

    print("[Consumer] Listening for order_placed events...")

    for message in consumer:
        event = message.value
        user_id = event.get("user_id")

        if not user_id:
            print("[Consumer] Skipping event, no user_id found")
            continue

        print(f"[Consumer] Received order_placed for user: {user_id}")

        db = SessionLocal()
        try:
            service = SegmentService(db)
            matched_segments = service.refresh_user_segments(user_id)
            print(f"[Consumer] User {user_id} now in segments: {matched_segments}")
        except Exception as e:
            print(f"[Consumer] Error processing user {user_id}: {e}")
        finally:
            db.close()

if __name__ == "__main__":
    main()