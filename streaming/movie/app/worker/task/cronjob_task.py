from app.worker import get_faust_app
import datetime
import time

# from app.worker.tables.count_table import count_table

faust_app = get_faust_app()


@faust_app.timer(30.0)
async def tass():
    print(datetime.datetime.now())
    time.sleep(5)
    print("ASDFSADFASDF", datetime.datetime.now())
