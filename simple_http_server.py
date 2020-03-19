import asyncio
import os
import sys
import traceback
from http.server import BaseHTTPRequestHandler
from io import BytesIO
from pprint import pprint


# https://stackoverflow.com/a/5955949/5318303
class HTTPRequest(BaseHTTPRequestHandler):
    # noinspection PyMissingConstructor
    def __init__(self, request_text):
        self.rfile = BytesIO(request_text)
        self.raw_requestline = self.rfile.readline()
        self.error_code = self.error_message = None
        self.parse_request()

    # noinspection PyMethodOverriding
    def send_error(self, code, message):
        self.error_code = code
        self.error_message = message


# pprint(dict(os.environ), width=1)
PORT = int(os.environ.get('PORT'))


async def handler(reader, writer):
    pprint(vars(writer.transport))
    # https://docs.python.org/3.4/library/asyncio-stream.html#streamreader
    try:
        data = b''
        while 1:
            chunk = await reader.read(0x1000)
            data += chunk
            reader.feed_eof()
            if reader.at_eof() or len(data) > 0x100000:
                break

        if not len(data):
            return

        request = HTTPRequest(data)

        pprint(vars(request))

        status, response_body = ['200 OK', 'pong'] if request.path == '/?ping' else ['404 Not Found', '']

        # https://stackoverflow.com/a/10114266/5318303
        response_headers = {
            'Content-Type': 'text/plain; encoding=utf8',
            'Content-Length': len(response_body),
            'Connection': 'close',
        }

        response_headers_raw = ''.join('%s: %s\n' % (k, v) for k, v in response_headers.items())
        print(response_headers_raw)

        response = 'HTTP/1.1 %s\n%s\n%s' % (status, response_headers_raw, response_body)
        writer.write(response.encode())
        await writer.drain()
        writer.write_eof()
        writer.close()
    except:
        print(traceback.format_exc(), file=sys.stderr)
    finally:
        try:
            response_headers = {
                'Content-Type': 'text/plain; encoding=utf8',
                'Content-Length': 0,
                'Connection': 'close',
            }
            response_headers_raw = ''.join('%s: %s\n' % (k, v) for k, v in response_headers.items())

            writer.write(('HTTP/1.1 %s\n%s\n' % ('503 Service Unavailable', response_headers_raw)).encode())
            await writer.drain()
            writer.write_eof()
        except RuntimeError as e:
            s = str(e)
            if s != 'write_eof() already called' and s != 'Cannot call write() after write_eof()':
                print(traceback.format_exc(), file=sys.stderr)
        except:
            print(traceback.format_exc(), file=sys.stderr)


# https://docs.python.org/3/library/asyncio-stream.html#tcp-echo-server-using-streams
async def serve():
    server = await asyncio.start_server(handler, '0.0.0.0', PORT)

    addr = server.sockets[0].getsockname()
    print(f'Serving on {addr}')

    async with server:
        # noinspection PyUnresolvedReferences
        await server.serve_forever()
