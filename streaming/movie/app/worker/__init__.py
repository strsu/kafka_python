import asyncio
from typing import Optional
import ssl
import os
import faust
from faust.auth import SASLCredentials

_faust_app: Optional[faust.App] = None

ssl_context = ssl.SSLContext()
ssl_context.verify_mode = ssl.CERT_NONE
ssl_context.check_hostname = False


def get_faust_app() -> Optional[faust.App]:
    return _faust_app


def set_faust_app_for_worker() -> Optional[faust.App]:
    global _faust_app

    if os.getenv("STAGE") == "local":
        _faust_app = faust.App(
            os.getenv("FAUST_WORKER_NAME"),
            topic_replication_factor=1,
            broker=os.getenv("FAUST_BROKER_URL", "").split(","),
            store=os.getenv("FAUST_STORE"),
            autodiscover=True,
            origin="app.worker",
            consumer_auto_offset_reset="latest",
        )
    else:
        _faust_app = faust.App(
            os.getenv("FAUST_WORKER_NAME"),
            topic_replication_factor=2,
            broker=os.getenv("FAUST_BROKER_URL", "").split(","),
            broker_credentials=SASLCredentials(
                username=os.getenv("KAFKA_SASL_USERNAME"),
                password=os.getenv("KAFKA_SASL_PASSWORD"),
                ssl_context=ssl_context,
                mechanism=os.getenv("KAFKA_SASL_MECHANISM"),
            ),
            store=os.getenv("FAUST_STORE"),
            autodiscover=True,
            origin="app.worker",
            consumer_auto_offset_reset="latest",
        )

    return _faust_app


def set_faust_app_for_api() -> Optional[faust.App]:
    global _faust_app

    _faust_app = faust.App(
        os.getenv("FAUST_WORKER_NAME"),
        topic_replication_factor=2,
        broker=os.getenv("FAUST_BROKER_URL", "").split(","),
        broker_credentials=SASLCredentials(
            username=os.getenv("KAFKA_SASL_USERNAME"),
            password=os.getenv("KAFKA_SASL_PASSWORD"),
            ssl_context=ssl_context,
            mechanism=os.getenv("KAFKA_SASL_MECHANISM"),
        ),
        autodiscover=True,
        origin="app.worker",
        loop=asyncio.get_running_loop(),
        reply_create_topic=True,
    )

    return _faust_app
