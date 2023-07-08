from kafka import KafkaProducer
import json
from datetime import datetime
import requests
import time
import ssl


def on_send_success(record_metadata):
    print("topic", record_metadata.topic)
    print("partition", record_metadata.partition)
    print("offset", record_metadata.offset)


def on_send_error(excp):
    print("I am an errback", exc_info=excp)
    # handle exception

ssl_context = ssl.SSLContext()
ssl_context.verify_mode = ssl.CERT_NONE
ssl_context.check_hostname = False


producer = KafkaProducer(
    api_version=(2,8,1), # kafka version
    security_protocol='SASL_SSL',
    sasl_mechanism='SCRAM-SHA-512',
    sasl_plain_username="admin",
    sasl_plain_password="admin",
    ssl_context = ssl_context,
    acks=1,
    compression_type="gzip",
    bootstrap_servers=["broker:29092"],
    value_serializer=lambda x: json.dumps(x).encode("utf-8"),
)

url = ""

headers = {
  'key': 'VRutvYidaBWrpSquwjnKKrbPgGKcwnEJ'
}

while True:
    response = requests.request("GET", url, headers=headers)
    if response.status_code == 200:
        data = response.json()
        producer.send("topic", value=data).add_callback(on_send_success).add_errback(
            on_send_error
        )
        producer.flush()  # block until all async messages are sent
        
    time.sleep(60)
    
