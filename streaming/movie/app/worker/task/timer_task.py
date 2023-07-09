from app.worker import get_faust_app
import datetime
import asyncio

# from app.worker.tables.count_table import count_table

faust_app = get_faust_app()


@faust_app.timer(60.0)
async def timer_test():
    print("timer_start", datetime.datetime.now())
    await asyncio.sleep(5)
    print("timer_end", datetime.datetime.now())
