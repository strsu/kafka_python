from prometheus_client import CollectorRegistry, Gauge, push_to_gateway
import time
import requests

registry = CollectorRegistry()
g = Gauge(
    "job_last_success_unixtime",
    "Last time a batch job successfully finished",
    registry=registry,
)
g.set_to_current_time()

prometheus_gateway = "192.168.1.243:9091"
job_name = "testt"

while True:
    # 데이터 생성 또는 수집 로직
    # 예시로 값을 증가시킴
    try:
        g.inc()  # +1

        push_to_gateway(prometheus_gateway, job=job_name, registry=registry)
    except Exception as e:
        print(e)

    # 1초 대기
    time.sleep(1)
