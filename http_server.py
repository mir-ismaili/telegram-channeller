import os

from aiohttp import web

PORT = int(os.environ.get('PORT') or 5000)


async def handler(request):
    if request.query_string == 'ping':
        return web.Response(text="pong")

    return web.Response(status=404)


# https://docs.aiohttp.org/en/stable/web_lowlevel.html#run-a-basic-low-level-server
async def serve():
    server = web.Server(handler)
    runner = web.ServerRunner(server)
    await runner.setup()
    site = web.TCPSite(runner, port=PORT)
    await site.start()

    print('Listening  on port %d ...' % PORT)

    # # pause here for very long time by serving HTTP requests and
    # # waiting for keyboard interruption
    # await asyncio.sleep(100*3600)
