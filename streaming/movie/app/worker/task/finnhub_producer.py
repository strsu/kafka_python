from app.worker import get_faust_app
import asyncio
import finnhub
import nest_asyncio
from kafka import KafkaProducer
import json
from datetime import datetime
import os

nest_asyncio.apply()

# from app.worker.tables.count_table import count_table

faust_app = get_faust_app()

finnhub_topic = faust_app.topic("finnhub")

finnhub_client = finnhub.Client(api_key="cijnmr9r01qgq27isd90cijnmr9r01qgq27isd9g")

symbol_list = [
    "ASTL",
    "NLY.PRF",
    "SBLRF",
    "RCEL",
    "CGASY",
    "AEGXF",
    "IESC",
    "KSA",
    "NVNXF",
    "RIVN",
    "CCLP",
    "MSOS",
    "TQLB",
    "SURE",
    "VTRU",
    "ARKX",
    "IBBQ",
    "LANV.WS",
    "GZPZF",
    "VAC",
    "DAIUF",
    "THC",
    "SMHB",
    "ADYRF",
    "SHOC",
    "PRO",
    "JPM",
    "PYHOF",
    "TOTTF",
    "MXTLF",
    "BMAY",
    "FXA",
    "AALBF",
    "DSTL",
    "GNGBY",
    "PBFS",
    "DECXF",
    "OROVY",
    "BSMP",
    "FPL",
    "XBIT",
    "STG",
    "WSNAF",
    "GMBLZ",
    "NMTC",
    "MTMV",
    "IDAT",
    "EBML",
    "MTLRF",
    "AIG.PRA",
]


def on_send_success(record_metadata):
    pass
    # print("topic", record_metadata.topic)
    # print("partition", record_metadata.partition)
    # print("offset", record_metadata.offset)


def on_send_error(excp):
    print("I am an errback", exc_info=excp)
    # handle exception


async def fetch(symbol):
    data = finnhub_client.quote(symbol)
    return {"symbol": symbol, **data}


async def main(symbol_list):
    futures = [asyncio.ensure_future(fetch(p)) for p in symbol_list]
    # 태스크(퓨처) 객체를 리스트로 만듦
    return await asyncio.gather(*futures)  # 결과를 한꺼번에 가져옴


@faust_app.task()
async def finnhub_producer():
    print("#### finnhub producer start ####")
    while True:
        try:
            if os.getenv("STAGE") == "local":
                producer = KafkaProducer(
                    acks=1,
                    compression_type="gzip",
                    bootstrap_servers=os.getenv("FAUST_BROKER_URL", "").split(","),
                    value_serializer=lambda x: json.dumps(x).encode("utf-8"),
                )
            else:
                producer = KafkaProducer(
                    api_version=(2, 8, 1),
                    security_protocol="SASL_SSL",
                    sasl_mechanism=os.getenv("KAFKA_SASL_MECHANISM"),
                    sasl_plain_username=os.getenv("KAFKA_SASL_USERNAME"),
                    sasl_plain_password=os.getenv("KAFKA_SASL_PASSWORD"),
                    acks=1,
                    compression_type="gzip",
                    bootstrap_servers=os.getenv("FAUST_BROKER_URL", "").split(","),
                    value_serializer=lambda x: json.dumps(x).encode("utf-8"),
                )

            loop = asyncio.get_event_loop()  # 이벤트 루프를 얻음
            execute_at = datetime.now().strftime("%H:%M")

            while True:
                if execute_at < datetime.now().strftime("%H:%M"):
                    result = loop.run_until_complete(
                        main(symbol_list[:20])
                    )  # main이 끝날 때까지 기다림
                    for data in result:
                        producer.send("finnhub", value=data).add_callback(
                            on_send_success
                        ).add_errback(on_send_error)

                        producer.flush()  # block until all async messages are sent
                    execute_at = datetime.now().strftime("%H:%M")
                while datetime.now().second > 10:
                    await asyncio.sleep(1)
        except:
            loop.close()  # 이벤트 루프를 닫음
            producer.close()
