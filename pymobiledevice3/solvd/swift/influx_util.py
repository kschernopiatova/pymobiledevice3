from influxdb_client_3 import InfluxDBClient3

from pymobiledevice3.solvd.data_util import get_config


class InfluxDBUtil:
    def __init__(self, start_time, end_time):
        db_config = get_config("../influxdb.properties")
        self.client = InfluxDBClient3(
            token=db_config.get("DB_TOKEN").data,
            host=db_config.get("DB_HOST").data,
            org=db_config.get("DB_ORG").data,
            database=db_config.get("DB_BUKET").data)
        self.start_time = start_time
        self.end_time = end_time

    def write_data(self, tags: dict):
        tag_names = list()
        for tag in tags:
            tag_names.append(tag)
        self.print_link(self.start_time, self.end_time, "graphics", tags)
        self.print_link(self.start_time, self.end_time, "energy", tags)
        self.print_link(self.start_time, self.end_time, "netstat", tags)
        self.print_link(self.start_time, self.end_time, "sysmon-monitor", tags)
        self.client.write_file(file='datajsons/graphics.csv', timestamp_column='time', tag_columns=tag_names)
        self.client.write_file(file='datajsons/energy_pid.csv', timestamp_column='time', tag_columns=tag_names)
        self.client.write_file(file='datajsons/netstat_pid.csv', timestamp_column='time', tag_columns=tag_names)
        self.client.write_file(file='datajsons/netstat.csv', timestamp_column='time', tag_columns=tag_names)
        self.client.write_file(file='datajsons/sysmon_pid.csv', timestamp_column='time', tag_columns=tag_names)
        self.client.write_file(file='datajsons/sysmon.csv', timestamp_column='time', tag_columns=tag_names)
        self.client.close()

    @staticmethod
    def print_link(start_time, end_time, metric, tags):
        unformatted_link = ("http://localhost:3000/d/{metric}/{dash}?orgId=1&from={start}&to={end}"
                            "&var-platform_name={platform}&var-os_version={os_version}"
                            "&var-device_name={device_name}&var-flow_id={flow}")
        print(unformatted_link.format(start=start_time, end=end_time, platform=tags["platform"], metric=metric,
                                      os_version=tags["os_version"], device_name=tags["device_name"], dash=metric,
                                      flow=tags["flowName"]))
