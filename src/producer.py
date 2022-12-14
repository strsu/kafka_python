from kafka import KafkaProducer
import json
import time
import arrow


def on_send_success(record_metadata):
    print("topic", record_metadata.topic)
    print("partition", record_metadata.partition)
    print("offset", record_metadata.offset)


def on_send_error(excp):
    print("I am an errback", exc_info=excp)
    # handle exception


producer = KafkaProducer(
    acks=1,
    compression_type="gzip",
    bootstrap_servers=["localhost:9092"],
    value_serializer=lambda x: json.dumps(x).encode("utf-8"),
)

for i in range(100):
    data = {"TEST": {"Text": "T" * 1000000, "Time": str(arrow.now("Asia/Seoul"))}}
    producer.send("topic", value=data).add_callback(on_send_success).add_errback(
        on_send_error
    )
producer.flush()  # block until all async messages are sent
# time.sleep(4)

# 문자열 길이: 백만 -> 0.013초 정도
