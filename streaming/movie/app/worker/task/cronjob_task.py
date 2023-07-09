from app.worker import get_faust_app
import datetime
import time
import pytz

# from app.worker.tables.count_table import count_table

faust_app = get_faust_app()


@faust_app.crontab("*/1 * * * *", tz=pytz.timezone("Asia/Seoul"), on_leader=False)
async def crontab_test():
    print("cron_start", datetime.datetime.now())
    # time.sleep(70)
    print("cron_end", datetime.datetime.now())
