from kafka import KafkaProducer
import json
import time
import random

# Kafka 브로커 주소 설정
bootstrap_servers = ["localhost:9092", "localhost:9094", "localhost:9096"]


# 메시지 직렬화 함수 (JSON 형식으로 변환)
def serializer(message):
    return json.dumps(message).encode("utf-8")


# KafkaProducer 인스턴스 생성
producer = KafkaProducer(
    bootstrap_servers=bootstrap_servers,
    value_serializer=serializer,
    acks="all",  # 모든 복제본이 메시지를 받았는지 확인
    retries=3,  # 실패 시 재시도 횟수
)

# 토픽명 설정
topic_name = "example-topic"


# 예제 메시지 데이터
def get_sample_data():
    return {
        "id": random.randint(1, 1000),
        "timestamp": time.time(),
        "message": f"샘플 메시지 #{random.randint(1, 100)}",
        "value": random.random() * 100,
    }


# 메시지 전송 콜백 함수
def on_success(record_metadata):
    print(
        f"메시지 전송 성공: {record_metadata.topic} 토픽의 파티션 {record_metadata.partition}, 오프셋 {record_metadata.offset}"
    )


def on_error(exception):
    print(f"메시지 전송 실패: {exception}")


# 여러 메시지 생성하여 전송
try:
    for _ in range(10):  # 10개의 메시지 전송
        data = get_sample_data()
        print(f"전송 데이터: {data}")

        # 메시지 전송 (비동기)
        future = producer.send(topic_name, value=data)
        future.add_callback(on_success).add_errback(on_error)

        time.sleep(1)  # 1초 간격으로 전송

    # 모든 메시지가 전송될 때까지 대기
    producer.flush()

except Exception as e:
    print(f"예외 발생: {e}")

finally:
    # 생산자 인스턴스 종료
    producer.close()
    print("생산자 종료됨")
