import logging
from perfomance import Performance, get_pid

logger = logging.getLogger(__name__)


if __name__ == "__main__":
    bundle = "com.apple.mobilesafari"
    perf = Performance()
    perf.start_collecting([get_pid(bundle)])
    perf.create_json()
