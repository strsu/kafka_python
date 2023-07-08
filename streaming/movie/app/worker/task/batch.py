from app.worker import get_faust_app
import faust
import os

# from app.worker.tables.count_table import count_table

faust_app = get_faust_app()

origin_topic = faust_app.topic("finnhub", replicas=1)
batch_topic = faust_app.topic("finnhub.batch", replicas=1)


@faust_app.agent(origin_topic)
async def agent(stream):
    async for event in stream:
        # event2 = [event_dict["after"] for event_dict in event]
        print(event)
        await batch_topic.send(value=event)
