import asyncio
import os
from time import time

import aiohttp
from persiantools.jdatetime import JalaliDateTime
from pytz import timezone

REMOTE_HOST = os.environ.get("REMOTE_HOST")

if REMOTE_HOST:
    url = f'https://{REMOTE_HOST}?ping'


    async def job():
        async with aiohttp.ClientSession() as session:
            start_time = time()
            async with session.get(url) as response:
                status = response.status
                response_body = await response.text()
                print('%s: Pinged %s / %.2fms / %d: %s' %
                      (JalaliDateTime.now(timezone('Iran')).strftime('%Y-%m-%d %H:%M:%S%Z'),
                       REMOTE_HOST, time() - start_time, status, response_body))


    async def cron():
        await asyncio.sleep(30)  # 30 seconds
        while 1:
            await job()
            await asyncio.sleep(10 * 60)  # 10 minutes

    # # test:
    # loop = asyncio.get_event_loop()
    # loop.run_until_complete(cron())
