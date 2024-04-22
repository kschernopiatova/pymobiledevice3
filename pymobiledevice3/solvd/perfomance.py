import datetime
import json
import logging
import re
import time
from threading import Thread

from RSD import start_tunnel
from pid_network import NetworkPID
from pymobiledevice3.remote.remote_service_discovery import RemoteServiceDiscoveryService
from pymobiledevice3.services.dvt.dvt_secure_socket_proxy import DvtSecureSocketProxyService
from pymobiledevice3.services.dvt.instruments.device_info import DeviceInfo
from pymobiledevice3.services.dvt.instruments.energy_monitor import EnergyMonitor
from pymobiledevice3.services.dvt.instruments.graphics import Graphics
from pymobiledevice3.services.dvt.instruments.network_monitor import NetworkMonitor
from pymobiledevice3.services.dvt.instruments.sysmontap import Sysmontap

logger = logging.getLogger(__name__)


class Performance:
    def __init__(self):
        self.condition = False
        self.netstat_pids = []
        self.graphics = []
        self.netstat_system = []
        self.energy_pid = []
        self.sysmon_processes = []
        self.sysmon_processes_pid = []
        self.host, self.port = start_tunnel()

    def monitor_graphics(self):
        logger.info("Graphics monitoring")
        with RemoteServiceDiscoveryService((self.host, self.port)) as rsd:
            with DvtSecureSocketProxyService(lockdown=rsd) as dvt:
                with Graphics(dvt) as graphics:
                    for stats in graphics:
                        stats["json_time"] = timestamp()
                        self.graphics.append(self.create_json_data(stats))
                        logger.info(stats)
                        if self.condition:
                            break

    def netstat(self):
        logger.info("Netstat monitoring")
        with RemoteServiceDiscoveryService((self.host, self.port)) as rsd:
            with DvtSecureSocketProxyService(lockdown=rsd) as dvt:
                with NetworkMonitor(dvt) as monitor:
                    for event in monitor:
                        self.netstat_system.append(self.create_json_data(event))
                        logger.info(event)
                        if self.condition:
                            break

    def netstat_pid(self, pid_list: list):
        print("Netstat monitoring by pid")
        with RemoteServiceDiscoveryService((self.host, self.port)) as rsd:
            with DvtSecureSocketProxyService(lockdown=rsd) as dvt:
                with NetworkPID(dvt, pid_list) as monitor:
                    for event in monitor:
                        if type(event) is dict:
                            data = get_dict_text(event)
                            self.netstat_pids.append(self.create_json_data(data))
                        logger.info(event)
                        if self.condition:
                            break

    def sysmon_process_monitor(self):
        logger.info("Sysmon monitoring")
        with RemoteServiceDiscoveryService((self.host, self.port)) as rsd:
            with DvtSecureSocketProxyService(lockdown=rsd) as dvt:
                with Sysmontap(dvt) as sysmon:
                    for process_snapshot in sysmon.iter_processes():
                        time.sleep(2)
                        for process in process_snapshot:
                            process["json_time"] = timestamp()
                            self.sysmon_processes.append(self.create_json_data(process))
                            logger.info(process)
                        if self.condition:
                            break

    def sysmon_process_monitor_pid(self, pid_list: list):
        logger.info("Sysmon monitoring by pid")
        with RemoteServiceDiscoveryService((self.host, self.port)) as rsd:
            with DvtSecureSocketProxyService(lockdown=rsd) as dvt:
                with Sysmontap(dvt) as sysmon:
                    for process_snapshot in sysmon.iter_processes():
                        for process in process_snapshot:
                            if process['pid'] in pid_list:
                                process["json_time"] = timestamp()
                                self.sysmon_processes_pid.append(self.create_json_data(process))
                                logger.info(process)
                        if self.condition:
                            break

    def dvt_energy(self, pid_list: list):
        logger.info("Energy monitoring by pid")
        with RemoteServiceDiscoveryService((self.host, self.port)) as rsd:
            with DvtSecureSocketProxyService(lockdown=rsd) as dvt:
                with EnergyMonitor(dvt, pid_list) as energy_monitor:
                    for telemetry in energy_monitor:
                        if type(telemetry) is dict:
                            data = get_dict_text(telemetry)
                            data = data.replace("'", "\"")
                            data = dict(json.loads(data))
                            data["json_time"] = timestamp()
                            self.energy_pid.append(self.create_json_data(data))
                        logger.info(telemetry)
                        if self.condition:
                            break

    def start_collecting(self, pid_list: list):
        energy_pid_daemon = Thread(target=self.dvt_energy, name="energy", daemon=True, kwargs={"pid_list": pid_list})
        energy_pid_daemon.start()
        time.sleep(2)
        sys_pid_daemon = Thread(target=self.sysmon_process_monitor_pid, name="sysmon_pid", daemon=True,
                                kwargs={"pid_list": pid_list})
        sys_pid_daemon.start()
        time.sleep(2)
        sys_daemon = Thread(target=self.sysmon_process_monitor, name="sysmon", daemon=True)
        sys_daemon.start()
        time.sleep(2)
        net_pid_daemon = Thread(target=self.netstat_pid, name="net_pid", daemon=True, kwargs={"pid_list": pid_list})
        net_pid_daemon.start()
        time.sleep(2)
        net_daemon = Thread(target=self.netstat, name="net", daemon=True)
        net_daemon.start()
        time.sleep(2)
        graphics_daemon = Thread(target=self.monitor_graphics, name="graph", daemon=True)
        graphics_daemon.start()

    def get_pid(self, bundle_id: str):
        str_data = self.proclist()
        json_data = json.loads(str_data)
        for item in json_data:
            if "bundleIdentifier" in item:
                if item["bundleIdentifier"] == bundle_id:
                    return item["pid"]

    def proclist(self):
        with RemoteServiceDiscoveryService((self.host, self.port)) as rsd:
            with DvtSecureSocketProxyService(lockdown=rsd) as dvt:
                processes = DeviceInfo(dvt).proclist()
                for process in processes:
                    if 'startDate' in process:
                        process['startDate'] = str(process['startDate'])
                return json.dumps(processes, sort_keys=True, indent=4)

    @staticmethod
    def create_json_data(data):
        data = str(data)
        data = data.replace("\n", "")
        data = data.replace("'", '"')
        data = data.replace("False", "false")
        data = data.replace("True", "true")
        data = data.replace("None", "null")
        return json.loads(data)

    def create_json(self):
        filtered_energy = list()
        for item in self.energy_pid:
            if type(item) is not set:
                filtered_energy.append(item)
        logger.info("Complete json")
        json_file = json.dumps({"system_performance":
                              {"graphics": self.graphics, "sysmon_monitor": self.sysmon_processes,
                               "netstat": {"events": self.netstat_system}},
                          "process_performance":
                              {"energy_pid": filtered_energy, "sysmon_monitor_pid": self.sysmon_processes_pid,
                               "netstat_pid": self.netstat_pids}
                          })
        with open("complete_json.json", 'w') as f:
            f.write(json_file)
        return json_file

    def stop_monitor(self):
        logger.info("Stop monitoring!")
        self.condition = True


def get_dict_text(dict_text: dict):
    data = str(dict(dict_text).values())
    data = re.search("dict_values\(\[(.*)\]\)", data)
    return data.group(1)


def timestamp():
    return datetime.datetime.now().timestamp()
