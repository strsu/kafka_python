from kafka_schema_registry import prepare_producer

SAMPLE_SCHEMA = {
    "type": "record",
    "name": "TestType",
    "fields": [
        {"name": "age", "type": "int"},
        {"name": "name", "type": ["null", "string"]},
    ],
}

topic_name = "topic"


producer = prepare_producer(
    ["broker:29092"],
    f"http://schemaregistry:8085",
    topic_name,
    1,
    1,
    value_schema=SAMPLE_SCHEMA,
)

producer.send(topic_name, {"age": 34})
producer.send(topic_name, {"age": 9000, "name": "john"})
