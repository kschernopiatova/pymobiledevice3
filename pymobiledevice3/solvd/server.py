from http.server import BaseHTTPRequestHandler, HTTPServer
from perfomance import Performance, get_pid

hostName = "localhost"
serverPort = 8080

perf = Performance()


class MyServer(BaseHTTPRequestHandler):

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        bundle = "com.apple.mobilesafari"
        global perf
        perf.start_collecting([get_pid(bundle)])

    def do_POST(self):
        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        global perf
        perf.stop_monitor()
        json_output = perf.create_json()
        self.wfile.write(bytes(json_output, "utf-8"))
        self.close_connection = True
        self.finish()


if __name__ == "__main__":
    webServer = HTTPServer((hostName, serverPort), MyServer)
    print("Server started http://%s:%s" % (hostName, serverPort))

    try:
        webServer.serve_forever()
    except KeyboardInterrupt:
        pass

    webServer.server_close()
    print("Server stopped.")