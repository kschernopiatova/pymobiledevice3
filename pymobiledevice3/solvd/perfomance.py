import json
import logging
import time
from threading import Thread

from RSD import start_tunnel
from pid_network import NetworkPID
from pymobiledevice3.cli.cli_common import print_json
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
        self.netstat_whole = []
        self.energy_PID = []
        self.sysmon_processes = []
        self.sysmon_processes_pid = []

    def monitor_graphics(self):
        print("Graphics monitoring")
        host, port = start_tunnel()
        with RemoteServiceDiscoveryService((host, port)) as rsd:
            with DvtSecureSocketProxyService(lockdown=rsd) as dvt:
                with Graphics(dvt) as graphics:
                    for stats in graphics:
                        self.graphics.append(stats)
                        logger.info(stats)
                        if self.condition:
                            break
        self.graphics = self.create_json_data_system(self.graphics)

    def netstat(self):
        print("Netstat monitoring")
        host, port = start_tunnel()
        with RemoteServiceDiscoveryService((host, port)) as rsd:
            with DvtSecureSocketProxyService(lockdown=rsd) as dvt:
                with NetworkMonitor(dvt) as monitor:
                    for event in monitor:
                        self.netstat_whole.append(event)
                        logger.info(event)
                        if self.condition:
                            break
        self.netstat_whole = self.create_json_data_system(self.netstat_whole)

    def netstat_pid(self, pid_list: list):
        print("Netstat monitoring by pid")
        host, port = start_tunnel()
        with RemoteServiceDiscoveryService((host, port)) as rsd:
            with DvtSecureSocketProxyService(lockdown=rsd) as dvt:
                with NetworkPID(dvt, pid_list) as monitor:
                    for event in monitor:
                        self.netstat_pids.append(event)
                        logger.info(event)
                        if self.condition:
                            break
        self.netstat_pids = self.create_json_data_process(self.netstat_pids, pid_list)

    def sysmon_process_monitor(self):
        print("Sysmon monitoring")
        host, port = start_tunnel()
        with RemoteServiceDiscoveryService((host, port)) as rsd:
            with DvtSecureSocketProxyService(lockdown=rsd) as dvt:
                with Sysmontap(dvt) as sysmon:
                    for process_snapshot in sysmon.iter_processes():
                        time.sleep(1.5)
                        for process in process_snapshot:
                            self.sysmon_processes.append(process)
                            print(process)
                        if self.condition:
                            break
        self.sysmon_processes = self.create_json_data_system(self.sysmon_processes)

    def sysmon_process_monitor_pid(self, pid_list: list):
        print("Sysmon monitoring by pid")
        host, port = start_tunnel()
        with RemoteServiceDiscoveryService((host, port)) as rsd:
            with DvtSecureSocketProxyService(lockdown=rsd) as dvt:
                with Sysmontap(dvt) as sysmon:
                    for process_snapshot in sysmon.iter_processes():
                        for process in process_snapshot:
                            if process['pid'] in pid_list:
                                self.sysmon_processes_pid.append(process)
                                logger.info(process)
                        if self.condition:
                            break
        self.sysmon_processes_pid = self.create_json_data_system(self.sysmon_processes_pid)

    def dvt_energy(self, pid_list: list):
        print("Energy monitoring by pid")
        host, port = start_tunnel()
        with RemoteServiceDiscoveryService((host, port)) as rsd:
            with DvtSecureSocketProxyService(lockdown=rsd) as dvt:
                with EnergyMonitor(dvt, pid_list) as energy_monitor:
                    for telemetry in energy_monitor:
                        self.energy_PID.append(telemetry)
                        logger.info(telemetry)
                        if self.condition:
                            break
        self.energy_PID = self.create_json_data_process(self.energy_PID, pid_list)

    def start_collecting(self, pid_list: list):
        energy_pid_daemon = Thread(target=self.dvt_energy, name="energy", daemon=True, kwargs={"pid_list": pid_list})
        energy_pid_daemon.start()
        time.sleep(1.5)
        graphics_daemon = Thread(target=self.monitor_graphics, name="graph", daemon=True)
        graphics_daemon.start()
        time.sleep(1.5)
        sys_pid_daemon = Thread(target=self.sysmon_process_monitor_pid, name="sysmon_pid", daemon=True,
                                kwargs={"pid_list": pid_list})
        sys_pid_daemon.start()
        time.sleep(1.5)
        sys_daemon = Thread(target=self.sysmon_process_monitor, name="sysmon", daemon=True)
        sys_daemon.start()
        time.sleep(1.5)
        net_pid_daemon = Thread(target=self.netstat_pid, name="net_pid", daemon=True, kwargs={"pid_list": pid_list})
        net_pid_daemon.start()
        time.sleep(1.5)
        net_daemon = Thread(target=self.netstat, name="net", daemon=True)
        net_daemon.start()
        time.sleep(7)

    @staticmethod
    def create_json_data_system(data):
        data = str(data)
        data = data.replace("\n", "")
        data = data.replace("'", '"')
        data = data.replace("False", "false")
        data = data.replace("True", "true")
        data = data.replace("None", "\"None\"")
        return json.loads(data)

    @staticmethod
    def create_json_data_process(data, pid_list: list):
        data = str(data)
        data = data.replace("\n", "")
        data = data.replace("'", '"')
        for pid in pid_list:
            data = data.replace(str(pid), str.format("\"%s\"", str(pid)))
        data = data.replace("False", "false")
        data = data.replace("True", "true")
        data = data.replace("None", "\"None\"")
        return json.loads(data)

    def create_json(self):
        filtered_energy = list()
        for item in self.energy_PID:
            if type(item) is not set:
                filtered_energy.append(item)
        print("Complete json")
        json_file = json.dumps({"system_performance":
                              {"graphics": self.graphics, "sysmon_monitor": self.sysmon_processes,
                               "netstat": self.netstat_whole},
                          "process_performance":
                              {"energy_pid": filtered_energy, "sysmon_monitor_pid": self.sysmon_processes_pid,
                               "netstat_pid": self.netstat_pids}
                          })
        with open("complete_json.json", 'w') as f:
            f.write(json_file)

    def stop_monitor(self):
        print("Stop monitoring!")
        self.condition = True


def get_pid(bundle_id: str):
    str_data = proclist()
    json_data = json.loads(str_data)
    for item in json_data:
        if "bundleIdentifier" in item:
            if item["bundleIdentifier"] == bundle_id:
                return item["pid"]


def proclist():
    host, port = start_tunnel()
    with RemoteServiceDiscoveryService((host, port)) as rsd:
        with DvtSecureSocketProxyService(lockdown=rsd) as dvt:
            processes = DeviceInfo(dvt).proclist()
            for process in processes:
                if 'startDate' in process:
                    process['startDate'] = str(process['startDate'])
            print_json(processes)
            return json.dumps(processes, sort_keys=True, indent=4)
