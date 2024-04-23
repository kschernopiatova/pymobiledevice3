import datetime
import logging
from http.server import BaseHTTPRequestHandler, HTTPServer

from pymobiledevice3.solvd.data_util import get_config
from pymobiledevice3.solvd.swift.influx_util import InfluxDBUtil
from pymobiledevice3.solvd.swift.perfomance_swift import PerformanceSwift

db_config = get_config("../server.properties")
hostName = db_config.get("host").data
serverPort = int(db_config.get("port").data)

perf: PerformanceSwift
tags: dict
logger = logging.getLogger(__name__)
start_time: int
end_time: int


class MyServer(BaseHTTPRequestHandler):

    def do_POST(self):
        self.send_response(200)
        bundle = self.headers.get("bundle")
        global perf, tags, start_time
        tags = dict()
        profile = self.headers.get("profile")
        tags["device_name"] = self.headers.get("device_name")
        tags["os_version"] = self.headers.get("os_version")
        tags["platform"] = self.headers.get("platform")
        tags["flowName"] = self.headers.get("flowName")
        tags["profile"] = profile
        perf = PerformanceSwift(tags)
        if not profile == "":
            perf.start_throttling(self.headers.get("profile"))
        start_time = datetime.datetime.now().timestamp() * 1000
        perf.start_collecting([perf.get_pid(bundle)])

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        global perf, tags, start_time, end_time
        end_time = datetime.datetime.now().timestamp() * 1000
        perf.stop_monitor()
        client = InfluxDBUtil(start_time, end_time)
        client.write_data(tags=tags)


if __name__ == "__main__":
    webServer = HTTPServer((hostName, serverPort), MyServer)
    logger.info("Server started http://%s:%s" % (hostName, serverPort))
    try:
        webServer.serve_forever()
    except KeyboardInterrupt:
        pass
    webServer.server_close()
    logger.info("Server stopped.")