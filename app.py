import asyncio

import http_server
import keep_service_alive
import telegram

if __name__ == '__main__':
    loop = asyncio.get_event_loop()

    loop.create_task(http_server.serve())
    loop.create_task(telegram.serve())
    loop.create_task(keep_service_alive.cron())
    try:
        loop.run_forever()
    finally:
        loop.run_until_complete(loop.shutdown_asyncgens())
        loop.close()
