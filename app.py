import asyncio

from telegram import Telegram

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    telegram = Telegram()
    loop.run_until_complete(telegram.init())

    # if os.environ.get('IS_ON_REMOTE'):
    #     loop.create_task(http_server.serve())
    #     loop.create_task(keep_service_alive.cron())
    loop.create_task(telegram.serve())

    try:
        loop.run_forever()
    finally:
        loop.run_until_complete(loop.shutdown_asyncgens())
        loop.close()
