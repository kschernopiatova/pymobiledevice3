import logging
import time
from threading import Thread
from perfomance import Performance, proclist, get_pid

logger = logging.getLogger(__name__)


if __name__ == "__main__":
    bundle = "com.apple.mobilesafari"
    perf = Performance()
    sysmon_pid_daemon = Thread(target=perf.sysmon_process_monitor, name="sysmon", daemon=True)
    sysmon_pid_daemon.start()
    time.sleep(10)
    perf.create_json()
