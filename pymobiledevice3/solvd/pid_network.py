import time

from pymobiledevice3.services.remote_server import MessageAux


class NetworkPID:
    IDENTIFIER = 'com.apple.xcode.debug-gauge-data-providers.NetworkStatistics'

    def __init__(self, dvt, pid_list: list):
        self._channel = dvt.make_channel(self.IDENTIFIER)
        self._pid_list = pid_list

    def __enter__(self):
        self._channel.startSamplingForPIDs_(MessageAux().append_obj(self._pid_list))
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._channel.stopSamplingForPIDs_(MessageAux().append_obj(self._pid_list))

    def __iter__(self):
        while True:
            time.sleep(1)
            self._channel.sampleAttributes_forPIDs_(MessageAux().append_obj({}).append_obj(self._pid_list))
            yield self._channel.receive_plist()
