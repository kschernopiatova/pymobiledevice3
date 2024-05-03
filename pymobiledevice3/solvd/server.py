import logging
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from perfomance import Performance

if len(sys.argv) >= 2:
    hostName = sys.argv[1]
    serverPort = int(sys.argv[2])
else:
    hostName = "localhost"
    serverPort = 8080

perf: Performance

logger = logging.getLogger(__name__)


class MyServer(BaseHTTPRequestHandler):

    def do_POST(self):
        self.send_response(200)
        bundle = self.headers.get("bundle")
        name = self.headers.get("name")
        self.end_headers()
        global perf
        perf = Performance()
        pid = perf.get_pid(bundle)
        if pid is None:
            pid = perf.get_pid_name(name)
        perf.start_collecting([pid])

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        global perf
        perf.stop_monitor()
        json_output = perf.create_json()
        self.wfile.write(bytes(json_output, "utf-8"))


if __name__ == "__main__":
    webServer = HTTPServer((hostName, serverPort), MyServer)
    logger.info("Server started http://%s:%s" % (hostName, serverPort))
    try:
        webServer.serve_forever()
    except KeyboardInterrupt:
        pass
    webServer.server_close()
    logger.info("Server stopped.")