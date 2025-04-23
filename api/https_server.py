from http.server import HTTPServer, SimpleHTTPRequestHandler
import ssl
import os

class MyHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=os.path.join(os.path.dirname(__file__), 'static'), **kwargs)

httpd = HTTPServer(('myapp.test', 8000), MyHandler)
httpd.socket = ssl.wrap_socket(
    httpd.socket,
    keyfile="key.pem",
    certfile="cert.pem",
    server_side=True
)
print("Сервер запущен: https://myapp.test:8000")
httpd.serve_forever()