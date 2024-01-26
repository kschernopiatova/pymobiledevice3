import time
from threading import Thread

from pymobiledevice3.cli.remote import cli_start_tunnel, get_port, get_host


def start_tunnel():
    daemon = Thread(target=cli_start_tunnel, daemon=True, name='Monitor')
    daemon.start()
    time.sleep(3)
    return get_host(), get_port()
