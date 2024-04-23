import json
import logging
import re
from datetime import datetime

import pandas as pd
from jproperties import Properties

logger = logging.getLogger(__name__)


def get_needed_metrics(item: str):
    keys = []
    line_count = 0
    with open("../metrics.properties") as f:
        for line in f.readlines():
            line_count += 1
            line = line.removesuffix("\n")
            if line == item:
                break
    with open("../metrics.properties") as f:
        for line in f.readlines()[line_count:]:
            if line == "\n":
                break
            metric = line.split("=")
            key = metric[0]
            value = metric[1].removesuffix("\n")
            if value == "true":
                keys.append(key)
    return keys


def add_items_to_dict(metrics: [str], old_dict: dict) -> dict:
    new_dict = dict()
    for item in metrics:
        if old_dict.__contains__(item):
            new_dict[item] = float(old_dict[item])
    return new_dict


def get_dict_text(dict_text: dict):
    data = str(dict(dict_text).values())
    data = re.search("dict_values\(\[(.*)\]\)", data)
    return data.group(1)


def writeToCsv(metrics, file_name):
    json_file = json.dumps(metrics)
    json_data = json.loads(json_file)
    df = pd.DataFrame(json_data)
    csv_file = "datajsons/" + file_name
    df.to_csv(csv_file, index=False)


def create_json_data(data):
    data = str(data)
    data = data.replace("\n", "")
    data = data.replace("'", '"')
    data = data.replace("False", "false")
    data = data.replace("True", "true")
    data = data.replace("None", "null")
    return json.loads(data)


def parse_profiles(profiles: str):
    if profiles != "":
        profiles = profiles.split(",")
        profiles.remove("")
    return profiles


def timestamp():
    return float(datetime.now().timestamp()) * 1000000000


def get_config(file: str) -> Properties:
    configs = Properties()
    with open(file, 'rb') as config:
        configs.load(config)
    return configs
