# Kafka CDC (Change Data Capture) Setup

이 프로젝트는 PostgreSQL 데이터베이스의 변경 사항을 Kafka로 스트리밍하는 CDC(Change Data Capture) 시스템을 구현합니다. Debezium을 사용하여 소스 데이터베이스의 변경 사항을 캡처하고, Kafka Connect JDBC Sink를 통해 타겟 데이터베이스에 복제합니다.

## 구성 요소

- **소스 PostgreSQL**: 원본 데이터 저장 (포트: 5442)
- **싱크 PostgreSQL**: 복제된 데이터 저장 (포트: 5443)
- **Kafka**: 메시지 브로커 시스템
- **Debezium 커넥터**: PostgreSQL의 변경 사항을 Kafka로 스트리밍
- **JDBC Sink 커넥터**: Kafka에서 타겟 PostgreSQL로 데이터 복제
- **Schema Registry**: Avro 스키마 관리

## 시작하기

### 사전 요구사항

- Docker와 Docker Compose 설치
- Python 3.7+

### 설치 및 실행

1. 전체 Kafka 클러스터 시작:
```bash
cd kafka-4
docker-compose up -d
```

2. CDC 관련 데이터베이스 시작:
```bash
cd kafka-4/cdc
docker-compose up -d
```

3. 테스트 데이터 생성기 실행:
```bash
cd kafka-4/cdc/dummy
pip install -r requirements.txt
python generator.py
```

## 커넥터 구성

### 소스 커넥터 (Debezium PostgreSQL)

`schema-registry-connector/source_connector.json` 파일에 정의된 설정으로 PostgreSQL의 변경 사항을 감지합니다. 

주요 설정:
- `connector.class`: `io.debezium.connector.postgresql.PostgresConnector`
- `database.server.name`: 데이터베이스 서버 식별자
- `plugin.name`: `pgoutput` (PostgreSQL 논리적 디코딩 플러그인)

### 싱크 커넥터 (JDBC Sink)

`schema-registry-connector/sink_connector.json` 파일에 정의된 설정으로 Kafka 토픽의 데이터를 타겟 PostgreSQL에 저장합니다.

주요 설정:
- `connector.class`: `io.confluent.connect.jdbc.JdbcSinkConnector`
- `insert.mode`: `upsert` (기존 레코드 업데이트)
- `pk.mode`: `record_key` (키를 기본 키로 사용)

## 알려진 문제 및 해결책

### 타임스탬프 변환 문제

**문제**: Debezium이 PostgreSQL의 타임스탬프를 캡처할 때 Unix 타임스탬프(bigint)로 변환하지만, PostgreSQL은 이를 timestamp 타입으로 기대합니다.

**해결책**: TimestampConverter 변환 적용
```json
"transforms": "unwrap,timestampCreate,timestampUpdate",
"transforms.timestampCreate.type": "org.apache.kafka.connect.transforms.TimestampConverter$Value",
"transforms.timestampCreate.field": "created_at",
"transforms.timestampCreate.target.type": "Timestamp",
"transforms.timestampUpdate.type": "org.apache.kafka.connect.transforms.TimestampConverter$Value",
"transforms.timestampUpdate.field": "updated_at",
"transforms.timestampUpdate.target.type": "Timestamp"
```

### 외래 키 제약 조건 위반

**문제**: 데이터 복제 순서로 인해 외래 키 제약 조건이 위반될 수 있습니다.

**해결책**: 오류 허용도 설정 적용
```json
"errors.tolerance": "all",
"errors.deadletterqueue.topic.name": "dlq_jdbc_sink_errors",
"errors.deadletterqueue.context.headers.enable": "true",
"errors.retry.timeout": "60000",
"errors.retry.delay.max.ms": "1000"
```

## 데이터 모델

데이터베이스는 다음 테이블로 구성됩니다:

1. **users**
   - user_id (PK)
   - username
   - email
   - created_at

2. **posts**
   - post_id (PK)
   - author_id (FK -> users.user_id)
   - title
   - content
   - created_at
   - updated_at

3. **comments**
   - comment_id (PK)
   - post_id (FK -> posts.post_id)
   - commenter_id (FK -> users.user_id)
   - comment_text
   - created_at

## 데이터 생성기 (generator.py)

`dummy/generator.py` 스크립트는:

1. 기존 커넥터 삭제
2. 스키마 레지스트리 주제 초기화
3. Kafka 토픽 초기화
4. 데이터베이스 스키마 설정
5. 초기 데이터 생성
6. 커넥터 생성
7. 지속적인 데이터 생성 및 검증

## 모니터링

1. Kafka UI: http://localhost:8080
2. Kafka Connect API: http://localhost:8083
3. Schema Registry API: http://localhost:8085

## 문제 해결

1. **커넥터 로그 확인**:
```bash
docker logs -f kafka-connect
```

2. **DLQ 확인**:
```bash
docker exec -it kafka1 /bin/kafka-console-consumer --bootstrap-server kafka1:29092 --topic dlq_jdbc_sink_errors
```

3. **커넥터 상태 확인**:
```bash
curl -s http://localhost:8083/connectors/sink-connector/status | jq
```

## 커넥터 관리

1. **커넥터 삭제**:
```bash
curl -X DELETE http://localhost:8083/connectors/sink-connector
```

2. **커넥터 생성/업데이트**:
```bash
curl -X POST -H "Content-Type: application/json" --data @sink_connector.json http://localhost:8083/connectors
```

3. **커넥터 재시작**:
```bash
curl -X POST http://localhost:8083/connectors/sink-connector/restart
```