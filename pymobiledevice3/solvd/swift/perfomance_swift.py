import json
import logging
import time
from threading import Thread

from pymobiledevice3.cli.cli_common import wait_return
from pymobiledevice3.remote.remote_service_discovery import RemoteServiceDiscoveryService
from pymobiledevice3.services.dvt.dvt_secure_socket_proxy import DvtSecureSocketProxyService
from pymobiledevice3.services.dvt.instruments.condition_inducer import ConditionInducer
from pymobiledevice3.services.dvt.instruments.device_info import DeviceInfo
from pymobiledevice3.services.dvt.instruments.energy_monitor import EnergyMonitor
from pymobiledevice3.services.dvt.instruments.graphics import Graphics
from pymobiledevice3.services.dvt.instruments.network_monitor import NetworkMonitor
from pymobiledevice3.services.dvt.instruments.sysmontap import Sysmontap
from pymobiledevice3.solvd.RSD import start_tunnel
from pymobiledevice3.solvd.data_util import timestamp, add_items_to_dict, create_json_data, get_dict_text, \
    writeToCsv, get_needed_metrics
from pymobiledevice3.solvd.pid_network import NetworkPID

logger = logging.getLogger(__name__)


class PerformanceSwift:
    def __init__(self, tags: dict):
        self.condition = False
        self.netstat_pids = []
        self.graphics = []
        self.netstat_system = []
        self.energy_pid = []
        self.sysmon_processes = []
        self.sysmon_processes_pid = []
        self.tags = tags
        self.host, self.port = start_tunnel()
        self.graphics_json = ""
        with RemoteServiceDiscoveryService((self.host, self.port)) as rsd:
            self.rsd = rsd
        with DvtSecureSocketProxyService(lockdown=self.rsd) as dvt:
            self.dvt = dvt

    def monitor_graphics(self):
        logger.info("Graphics monitoring")
        graphics_metrics = get_needed_metrics("Graphics")
        with DvtSecureSocketProxyService(lockdown=self.rsd) as dvt:
            with Graphics(dvt) as graphics:
                for stats in graphics:
                    new_stat = add_items_to_dict(graphics_metrics, stats)
                    new_stat["iox::measurement"] = "graphics"
                    for tag in self.tags:
                        new_stat[tag] = self.tags[tag]
                    new_stat["time"] = timestamp()
                    self.graphics.append(create_json_data(new_stat))
                    if self.condition:
                        break

    def netstat(self):
        logger.info("Netstat monitoring")
        net_metrics = get_needed_metrics("Netstat")
        with DvtSecureSocketProxyService(lockdown=self.rsd) as dvt:
            with NetworkMonitor(dvt) as monitor:
                time.sleep(3)
                for event in monitor:
                    if event.keys().__contains__("ConnectionUpdateEvent"):
                        event = event["ConnectionUpdateEvent"]
                        new_event = add_items_to_dict(net_metrics, event)
                        new_event["time"] = event["time"]
                        new_event["iox::measurement"] = "netstat"
                        for tag in self.tags:
                            new_event[tag] = self.tags[tag]
                        self.netstat_system.append(create_json_data(new_event))
                    if self.condition:
                        break

    def netstat_pid(self, pid_list: list):
        logger.info("Netstat monitoring by pid")
        net_pid_metrics = get_needed_metrics("Netstat_pid")
        with DvtSecureSocketProxyService(lockdown=self.rsd) as dvt:
            with NetworkPID(dvt, pid_list) as monitor:
                for event in monitor:
                    if type(event) is dict:
                        data = get_dict_text(event)
                        data = data.replace("'", "\"")
                        data = dict(json.loads(data))
                        del data["time"]
                        new_event = add_items_to_dict(net_pid_metrics, data)
                        new_event["time"] = timestamp()
                        new_event["iox::measurement"] = "netstat_pid"
                        for tag in self.tags:
                            new_event[tag] = self.tags[tag]
                        self.netstat_pids.append(create_json_data(new_event))
                    if self.condition:
                        break

    def sysmon_process_monitor(self):
        logger.info("Sysmon monitoring")
        sysmon_metrics = get_needed_metrics("Sysmon")
        with DvtSecureSocketProxyService(lockdown=self.rsd) as dvt:
            with Sysmontap(dvt) as sysmon:
                for process_snapshot in sysmon.iter_processes():
                    for process in process_snapshot:
                        time.sleep(2)
                        new_proc = add_items_to_dict(sysmon_metrics, process)
                        new_proc["time"] = timestamp()
                        new_proc["iox::measurement"] = "sysmon"
                        for tag in self.tags:
                            new_proc[tag] = self.tags[tag]
                        self.sysmon_processes.append(create_json_data(new_proc))
                    if self.condition:
                        break

    def sysmon_process_monitor_pid(self, pid_list: list):
        logger.info("Sysmon monitoring by pid")
        sysmon_metrics = get_needed_metrics("Sysmon")
        with DvtSecureSocketProxyService(lockdown=self.rsd) as dvt:
            with Sysmontap(dvt) as sysmon:
                for process_snapshot in sysmon.iter_processes():
                    for process in process_snapshot:
                        if process['pid'] in pid_list:
                            new_proc = add_items_to_dict(sysmon_metrics, process)
                            new_proc["time"] = timestamp()
                            new_proc["iox::measurement"] = "sysmon"
                            for tag in self.tags:
                                new_proc[tag] = self.tags[tag]
                            self.sysmon_processes_pid.append(create_json_data(new_proc))
                    if self.condition:
                        break

    def dvt_energy(self, pid_list: list):
        logger.info("Energy monitoring by pid")
        energy_metrics = get_needed_metrics("Energy")
        with DvtSecureSocketProxyService(lockdown=self.rsd) as dvt:
            with EnergyMonitor(dvt, pid_list) as energy_monitor:
                for telemetry in energy_monitor:
                    if type(telemetry) is dict:
                        data = get_dict_text(telemetry)
                        data = data.replace("'", "\"")
                        data = dict(json.loads(data))
                        new_data = add_items_to_dict(energy_metrics, data)
                        new_data["time"] = timestamp()
                        new_data["iox::measurement"] = "energy"
                        for tag in self.tags:
                            new_data[tag] = self.tags[tag]
                        self.energy_pid.append(create_json_data(new_data))
                    if self.condition:
                        break

    def induce_state(self, profile: str):
        with DvtSecureSocketProxyService(lockdown=self.rsd) as dvt:
            inducer = ConditionInducer(dvt)
            inducer.set(profile)
            wait_return()

    def start_throttling(self, profile):
        inducer_daemon = Thread(target=self.induce_state, daemon=True, kwargs={"profile": profile})
        inducer_daemon.start()

    def start_collecting(self, pid_list: list):
        energy_pid_daemon = Thread(target=self.dvt_energy, name="energy", daemon=True, kwargs={"pid_list": pid_list})
        energy_pid_daemon.start()
        time.sleep(1.5)
        net_pid_daemon = Thread(target=self.netstat_pid, name="net_pid", daemon=True, kwargs={"pid_list": pid_list})
        net_pid_daemon.start()
        time.sleep(1.5)
        net_daemon = Thread(target=self.netstat, name="net", daemon=True)
        net_daemon.start()
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

    def stop_monitor(self):
        logger.info("Stop monitoring!")
        self.condition = True
        self.create_csvs()

    def create_csvs(self):
        filtered_energy = list()
        for item in self.energy_pid:
            if type(item) is not set:
                filtered_energy.append(item)
        writeToCsv(self.sysmon_processes, "sysmon.csv")
        writeToCsv(self.sysmon_processes_pid, "sysmon_pid.csv")
        writeToCsv(self.netstat_system, "netstat.csv")
        writeToCsv(self.netstat_pids, "netstat_pid.csv")
        writeToCsv(self.graphics, "graphics.csv")
        writeToCsv(self.energy_pid, "energy_pid.csv")
