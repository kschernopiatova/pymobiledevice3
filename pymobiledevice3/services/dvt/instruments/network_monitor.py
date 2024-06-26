import dataclasses
import ipaddress
import logging
from datetime import datetime

from construct import Adapter, Bytes, Int8ul, Int16ub, Int32ul, Struct, Switch, this


class IpAddressAdapter(Adapter):
    def _decode(self, obj, context, path):
        return ipaddress.ip_address(obj)


address_t = Struct(
    'len' / Int8ul,
    'family' / Int8ul,
    'port' / Int16ub,
    'data' / Switch(this.len, {
        0x1c: Struct(
            'flow_info' / Int32ul,
            'address' / IpAddressAdapter(Bytes(16)),
            'scope_id' / Int32ul,
        ),
        0x10: Struct(
            'address' / IpAddressAdapter(Bytes(4)),
            '_zero' / Bytes(8)
        )
    })

)

MESSAGE_TYPE_INTERFACE_DETECTION = 0
MESSAGE_TYPE_CONNECTION_DETECTION = 1
MESSAGE_TYPE_CONNECTION_UPDATE = 2


@dataclasses.dataclass
class InterfaceDetectionEvent:
    interface_index: int
    name: str

    def get_dump(self):
        return {"InterfaceDetectionEvent":
                               {"interface_index": self.interface_index,
                                "name": self.name,
                                "json_time": datetime.now().timestamp()}}


@dataclasses.dataclass
class ConnectionDetectionEvent:
    local_address: str
    remote_address: str
    interface_index: int
    pid: int
    recv_buffer_size: int
    recv_buffer_used: int
    serial_number: int
    kind: int

    def get_dump(self):
        return {"ConnectionDetectionEvent":
                               {"interface_index": self.interface_index,
                                "pid": self.pid,
                                "recv_buffer_size": self.recv_buffer_size,
                                "recv_buffer_used": self.recv_buffer_used,
                                "serial_number": self.serial_number,
                                "kind": self.kind,
                                "json_time": datetime.now().timestamp()}}


@dataclasses.dataclass
class ConnectionUpdateEvent:
    rx_packets: int
    rx_bytes: int
    tx_bytes: int
    rx_dups: int
    rx000: int
    tx_retx: int
    min_rtt: int
    avg_rtt: int
    connection_serial: int
    unknown0: int
    unknown1: int

    def get_dump(self):
        return {"ConnectionUpdateEvent":
                               {"rx_packets": self.rx_packets,
                                "rx_bytes": self.rx_bytes,
                                "tx_bytes": self.tx_bytes,
                                "rx_dups": self.rx_dups,
                                "rx000": self.rx000,
                                "tx_retx": self.tx_retx,
                                "min_rtt": self.min_rtt,
                                "avg_rtt": self.avg_rtt,
                                "connection_serial": self.connection_serial,
                                "unknown0": self.unknown0,
                                "unknown1": self.unknown1,
                                "json_time": datetime.now().timestamp()}}


class NetworkMonitor:
    IDENTIFIER = 'com.apple.instruments.server.services.networking'

    def __init__(self, dvt):
        self.logger = logging.getLogger(__name__)
        self._channel = dvt.make_channel(self.IDENTIFIER)

    def __enter__(self):
        self._channel.startMonitoring(expects_reply=False)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._channel.stopMonitoring()

    def __iter__(self):
        while True:
            message = self._channel.receive_plist()

            event = None

            if message is None:
                continue

            if message[0] == MESSAGE_TYPE_INTERFACE_DETECTION:
                event = InterfaceDetectionEvent(*message[1])
                event = event.get_dump()
            elif message[0] == MESSAGE_TYPE_CONNECTION_DETECTION:
                event = ConnectionDetectionEvent(*message[1])
                # event.local_address = address_t.parse(event.local_address)
                # event.remote_address = address_t.parse(event.remote_address)
                event = event.get_dump()
            elif message[0] == MESSAGE_TYPE_CONNECTION_UPDATE:
                event = ConnectionUpdateEvent(*message[1])
                event = event.get_dump()
            else:
                self.logger.warning(f'unsupported event type: {message[0]}')
            yield event
