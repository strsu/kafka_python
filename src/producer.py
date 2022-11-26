from kafka import KafkaProducer
import json
import time
import arrow

producer = KafkaProducer(
    acks=0,
    compression_type="gzip",
    bootstrap_servers=["localhost:9092"],
    value_serializer=lambda x: json.dumps(x).encode("utf-8"),
)

for i in range(100):
    data = {"time": arrow.now("Asia/Seoul").format("YYYY-MM-DD HH:mm:ss")}
    producer.send("test", value=data)
    producer.flush()
    time.sleep(4)
