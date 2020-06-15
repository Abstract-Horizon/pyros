
#
# Copyright 2016-2017 Games Creators Club
#
# MIT License
#

import traceback
import pyroslib
# import time

_first_values = {}
storage_map = {}


def has_data_at(path):
    value = read(path)
    return value is not None and value != ""


def read(path):
    split_path = path.split("/")

    m = storage_map
    for i in range(0, len(split_path) - 1):
        key = split_path[i]
        if key not in m:
            return None
        m = m[key]
    key = split_path[len(split_path) - 1]

    if key not in m:
        return None

    return m[key]


def write(path, value):
    split_path = path.split("/")

    m = storage_map
    for i in range(0, len(split_path) - 1):
        key = split_path[i]
        if key not in m:
            if value == "":
                return  # empty string means no data. No data - no change.
            m[key] = {}
            # change = True
        m = m[key]
    key = split_path[len(split_path) - 1]
    m[key] = value

    pyroslib.publish("storage/write/" + path, value)


def _handle_values(topic, message, _groups):
    global _first_values

    # change = False
    value = message
    split_path = topic.split("/")
    del split_path[0]
    del split_path[0]

    topic = "/".join(split_path)
    if topic in _first_values:
        del _first_values[topic]

    m = storage_map
    for i in range(0, len(split_path) - 1):
        key = split_path[i]
        if key not in m:
            if value == "":
                return  # empty string means no data. No data - no change.
            m[key] = {}
            # change = True
        m = m[key]
    key = split_path[len(split_path) - 1]

    if (key not in m and value != "") or (key in m and m[key] != value):
        # change = True
        m[key] = value


def subscribe_to_path(path):
    topic = "storage/write/" + path
    pyroslib.subscribe(topic, _handle_values)

    _first_values[path] = None

    topic = "storage/read/" + path
    pyroslib.publish(topic, "")


def subscribe_with_prototype(prefix, proto_map):
    for key in proto_map:
        if prefix is None or prefix is dict:
            path = key
        else:
            path = prefix + "/" + key
        if type(proto_map[key]) is dict:
            subscribe_with_prototype(path, proto_map[key])
        else:
            subscribe_to_path(path)


def bulk_populate_if_empty(prefix, proto_map):

    def process_recursively(storage, prefix_r, proto_map_r):
        for key in proto_map_r:
            if prefix_r is None or prefix_r is dict:
                path = key
            else:
                path = prefix_r + "/" + key
            if type(proto_map_r[key]) is dict:
                if key not in storage:
                    storage[key] = {}

                    process_recursively(storage[key], path, proto_map_r[key])
            else:
                subscribe_to_path(path)

    m = storage_map
    if prefix != "" and prefix is not None:
        split_path = prefix.split("/")
        for k in split_path:
            if k not in m:
                m[k] = {}
            m = m[k]

    process_recursively(m, prefix, proto_map)


def wait_for_data():
    while len(_first_values) > 0:
        try:
            for path in _first_values:
                topic = "storage/read/" + path
                pyroslib.publish(topic, "")
            pyroslib.loop(1)
        except Exception as ex:
            print("ERROR: Got exception in main loop; " + str(ex) + "\n" + ''.join(traceback.format_tb(ex.__traceback__)))


if __name__ == "__main__":

    pyroslib.init("storagelib")
