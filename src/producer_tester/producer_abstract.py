from kafka import KafkaProducer
import json
from datetime import datetime
import ssl
import time


class VppProducer:
    def __init__(self, is_sasl_ssl=False, bootstrap_servers=["broker:29092"]):
        self.is_sasl_ssl = is_sasl_ssl
        self.bootstrap_servers = bootstrap_servers

        self.connect()

    def connect(self):
        if self.is_sasl_ssl:
            ssl_context = ssl.SSLContext()
            ssl_context.verify_mode = ssl.CERT_NONE
            ssl_context.check_hostname = False

            self.producer = KafkaProducer(
                acks=1,
                compression_type="gzip",
                bootstrap_servers=self.bootstrap_servers,
                api_version=(2, 8, 1),  # kafka version
                security_protocol="SASL_SSL",
                sasl_mechanism="SCRAM-SHA-512",
                sasl_plain_username="admin",
                sasl_plain_password="admin",
                ssl_context=ssl_context,
                value_serializer=lambda x: json.dumps(x).encode("utf-8"),
            )
        else:
            self.producer = KafkaProducer(
                acks=1,
                compression_type="gzip",
                bootstrap_servers=self.bootstrap_servers,
                value_serializer=lambda x: json.dumps(x).encode("utf-8"),
            )

    def on_send_success(self, record_metadata):
        pass
        # print("topic", record_metadata.topic)
        # print("partition", record_metadata.partition)
        # print("offset", record_metadata.offset)

    def on_send_error(self, excp):
        # handle exception
        print("## I am an errback", excp)
        if not self.is_bootstrap_connected():
            print("## Producer - Broker Connect Fail")
            self.connect()
            time.sleep(1)

    def send(self, topic, data_list):
        try:
            for data in data_list:
                self.producer.send(topic, value=data).add_callback(
                    self.on_send_success
                ).add_errback(self.on_send_error)

            self.producer.flush()  # block until all async messages are sent
        except Exception as e:
            print("## Producer Send Error,", e)
            if not self.is_bootstrap_connected():
                print("## Producer - Broker Connect Fail")
                self.connect()
                time.sleep(1)

    def is_bootstrap_connected(self):
        return self.producer.bootstrap_connected()

    def get_metrics(self):
        return self.producer.metrics()
