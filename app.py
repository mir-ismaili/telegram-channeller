#!/usr/bin/env python
import logging
import os
import pprint
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler, SimpleHTTPRequestHandler

pprint.pprint(dict(os.environ), width=1)
print(sys.argv[0:])

if not __name__ == "__main__":
    sys.exit()

Handler = SimpleHTTPRequestHandler


class ProxyHTTPRequestHandler(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.0'

    def do_GET(self, body=True):
        try:
            if not self.path == '/?ping':
                self.send_response(404)
                self.end_headers()
                self.wfile.write('pong'.encode('utf8'))
                self.wfile.flush()
                return
            req_header = self.headers
            # pprint.pprint(dict(req_header), width=1)
            print(self.path)
            self.send_response(200)
            # self.send_resp_headers(req_header, 11)
            self.end_headers()
            self.wfile.write('pong'.encode('utf8'))
            self.wfile.flush()
            return
        except Exception as e:
            logging.error('Error at %s', 'division', exc_info=e)
        # finally:
        #     print('A')
        #     try:
        #         self.finish()
        #     except:
        #         pass


# with socketserver.TCPServer(("", PORT), BaseHTTPRequestHandler) as httpd:
#     print("serving at port", PORT)
#     httpd.serve_forever()

PORT = int(os.environ.get("PORT"))
print(PORT)
server_address = ('', PORT)
httpd = HTTPServer(server_address, ProxyHTTPRequestHandler)
print("Serving on:", PORT)
httpd.serve_forever()
