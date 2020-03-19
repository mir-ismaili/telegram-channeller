import asyncio
import os

import aiohttp

# from icu import DateFormat, Formattable

REMOTE_HOST = os.environ.get("REMOTE_HOST")

if REMOTE_HOST:
    url = f'https://{REMOTE_HOST}?ping'


    async def job():
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                status = response.status
                response_body = await response.text()
                print('%s: Pinged: / %d: %s' % (REMOTE_HOST, status, response_body))


    async def cron():
        while 1:
            await job()
            await asyncio.sleep(10 * 60)  # 10 minutes

    # # test:
    # loop = asyncio.get_event_loop()
    # loop.run_until_complete(cron())
