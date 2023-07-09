from app.worker import get_faust_app
import faust
import os

# from app.worker.tables.count_table import count_table

faust_app = get_faust_app()

origin_topic = faust_app.topic("finnhub", replicas=1)
batch_topic = faust_app.topic("finnhub.batch", replicas=1)


@faust_app.agent(origin_topic)
async def agent(stream):
    async for event in stream.take(5, within=10):
        """
           max — the maximum number of messages in the batch, 5개를 가져온다.
        within — timeout for waiting to receive max_ messages, 최대 10초 까지만 기다린다.

        이렇게 배치로 갖오면 5개의 메세지가 하나의 Topic으로 들어간다.

        """
        # print(event)
        await batch_topic.send(value=event)
