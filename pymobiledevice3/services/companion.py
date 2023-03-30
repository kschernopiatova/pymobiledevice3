#!/usr/bin/env python3
from typing import Any, Mapping

from pymobiledevice3.exceptions import PyMobileDevice3Exception
from pymobiledevice3.lockdown import LockdownClient
from pymobiledevice3.services.base_service import BaseService


class CompanionProxyService(BaseService):
    SERVICE_NAME = 'com.apple.companion_proxy'

    def __init__(self, lockdown: LockdownClient):
        super().__init__(lockdown, self.SERVICE_NAME)

    def list(self) -> Mapping:
        service = self.lockdown.start_service(self.SERVICE_NAME)
        return service.send_recv_plist({'Command': 'GetDeviceRegistry'}).get('PairedDevicesArray', [])

    def listen_for_devices(self) -> Mapping:
        service = self.lockdown.start_service(self.SERVICE_NAME)
        service.send_plist({'Command': 'StartListeningForDevices'})
        while True:
            yield service.recv_plist()

    def get_value(self, udid: str, key: str) -> Any:
        service = self.lockdown.start_service(self.SERVICE_NAME)
        response = service.send_recv_plist({'Command': 'GetValueFromRegistry',
                                            'GetValueGizmoUDIDKey': udid,
                                            'GetValueKeyKey': key})

        value = response.get('RetrievedValueDictionary')
        if value is not None:
            return value

        error = response.get('Error')
        raise PyMobileDevice3Exception(error)

    def start_forwarding_service_port(self, remote_port: int, service_name: str = None,
                                      options: Mapping = None) -> Any:
        service = self.lockdown.start_service(self.SERVICE_NAME)

        request = {'Command': 'StartForwardingServicePort',
                   'GizmoRemotePortNumber': remote_port,
                   'IsServiceLowPriority': False,
                   'PreferWifi': False}

        if service_name is not None:
            request['ForwardedServiceName'] = service_name

        if options is not None:
            request.update(options)

        return service.send_recv_plist(request).get('CompanionProxyServicePort')

    def stop_forwarding_service_port(self, remote_port: int) -> Mapping:
        service = self.lockdown.start_service(self.SERVICE_NAME)

        request = {'Command': 'StopForwardingServicePort',
                   'GizmoRemotePortNumber': remote_port}

        return service.send_recv_plist(request)
