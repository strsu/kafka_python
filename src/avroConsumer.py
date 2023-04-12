import json
from confluent_kafka import Producer, KafkaException
from confluent_kafka.avro import AvroConsumer
from confluent_kafka import avro


def read_data():
    consumer_config = {
        "bootstrap.servers": "broker:29092",
        "schema.registry.url": "http://schemaregistry:8085",
        "group.id": "my-connsumer1",
        "auto.offset.reset": "earliest",
    }

    # print(key_schema)
    # print(value_schema)

    consumer = AvroConsumer(consumer_config)
    consumer.subscribe(["movie-topic"])

    while True:
        try:
            msg = consumer.poll(1)

            if msg is None:
                continue

            print("Key is :" + json.dumps(msg.key()))
            print("Value is :" + json.dumps(msg.value()))
            print("-------------------------")

        except KafkaException as e:
            print("Kafka failure " + e)

    consumer.close()


def main():
    read_data()


if __name__ == "__main__":
    main()
