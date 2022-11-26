from kafka import KafkaConsumer
import json

consumer = KafkaConsumer(
    "topic",
    bootstrap_servers=["localhost:9092"],
    auto_offset_reset="earliest",
    enable_auto_commit=True,
    group_id="my_group",
    value_deserializer=lambda x: json.loads(x.decode("utf-8")),
    consumer_timeout_ms=1000,
)

while True:
    for msg in consumer:
        value = msg.value
        print(f"time: {value['TEST']['Time']}")
