import os
import xmltodict

configpath = "resource/config.xml"
xmlconfig = {}

if not os.path.isfile(configpath):
    raise RuntimeError("Config file not found!")

with open(configpath, 'r') as file:
    xmlconfig = xmltodict.parse(file.read())

if xmlconfig is None:
    raise RuntimeError("Unable to read config file!")

if xmlconfig.get("MyQSLConfig") is None:
    raise RuntimeError("Missing <MyQSLConfig> block in config file")


def get_config(path):
    path_list = path.split("/")

    # Settings/Database
    current_level = xmlconfig["MyQSLConfig"]
    for i in path_list:
        if current_level.get(i) is None:
            raise RuntimeError("BAD CONFIG: <" + i + "> config block not found")

        current_level = current_level[i]

    return current_level
