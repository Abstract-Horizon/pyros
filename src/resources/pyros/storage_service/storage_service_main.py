#!/usr/bin/env python3

#
# Copyright 2016-2017 Games Creators Club
#
# MIT License
#

import os
import time
import traceback
import pyroslib

#
# storage service
#
# This service is just storing 'storage map' to disk and reads it at the start up.
# Also, responds to requests for it to be read out completely or particular keys separately
#

DEBUG = False

STORAGE_MAP_FILE = os.path.expanduser('~') + "/rover-storage.config"

storageMap = {}


def add_paths(p1, p2):
    if "" == p1:
        return p2
    return p1 + "/" + p2


def write_local_storage(m):
    def write_layer(f, mm, path):
        for k in mm:
            p = add_paths(path, k)
            v = mm[k]
            if isinstance(v, dict):
                write_layer(f, v, p)
            else:
                f.write(p + "=" + str(v) + "\n")

    with open(STORAGE_MAP_FILE, 'wt') as file:
        file.write("; storage written at " + time.ctime(time.time()) + "\n")
        write_layer(file, m, "")


def load_storage_map():
    global storageMap

    storageMap = {}

    if os.path.exists(STORAGE_MAP_FILE):
        with open(STORAGE_MAP_FILE, "rt") as file:
            lines = file.readlines()

        for line in lines:
            line = line.strip()
            if not line.startswith(";"):
                i = line.find("=")
                if i > 0:
                    k = line[0:i]
                    v = line[i + 1:]
                    write_storage(k.split("/"), v)

        print("  Storage map is " + str(storageMap))
    else:
        print("  No storage map found @ " + STORAGE_MAP_FILE)


def _compose_recursively(m, prefix):
    res = ""
    for key in m:
        if type(m[key]) is dict:
            new_prefix = prefix + key + "/"
            res += _compose_recursively(m[key], new_prefix)
        else:
            res += prefix + key + "=" + str(m[key]) + "\n"

    return res


def readout_storage():
    pyroslib.publish("storage/values", _compose_recursively(storageMap, ""))


def write_storage(split_path, value):
    # print("Got storage value " + str(topicSplit))
    change = False

    m = storageMap
    for i in range(0, len(split_path) - 1):
        key = str(split_path[i])
        if key not in m:
            if value == "":
                return  # empty string means no data. No data - no change.
            m[key] = {}
            change = True
        m = m[key]
    key = str(split_path[len(split_path) - 1])

    if (key not in m and value != "") or (key in m and m[key] != value):
        change = True
        m[key] = value

    if change:
        if DEBUG:
            print("Storing to storage " + str(split_path) + " = " + value)

        write_local_storage(storageMap)


def read_storage(split_path):
    m = storageMap
    for i in range(0, len(split_path) - 1):
        key = str(split_path[i])
        if key not in m or not isinstance(m, dict):
            if DEBUG:
                print("Reading - not found key for " + "/".join(split_path))
            pyroslib.publish("storage/write/" + "/".join(split_path), "")
            return
        m = m[key]
    key = str(split_path[len(split_path) - 1])

    if key not in m:
        if DEBUG:
            print("Reading - not found key for " + "/".join(split_path))
        pyroslib.publish("storage/write/" + "/".join(split_path), "")
    else:
        if type(m[key]) is dict:
            if DEBUG:
                print("Reading - found map at " + "/".join(split_path))
            _read_recursively("/".join(split_path), m[key])
        else:
            value = str(m[key])
            if DEBUG:
                print("Reading - found key for " + "/".join(split_path) + " = " + value)
            pyroslib.publish("storage/write/" + "/".join(split_path), value)


def _read_recursively(path, m):
    for key in m:
        if type(m[key]) is dict:
            _read_recursively(path + "/" + key, m[key])
        else:
            value = str(m[key])
            if DEBUG:
                print("Reading - found key for " + path + " = " + value)
            pyroslib.publish("storage/write/" + path + "/" + key, value)


def storage_write_topic(_topic, payload, groups):
    write_storage(groups[0].split("/"), payload)


def storage_read_all_topic(_topic, _payload, _groups):
    if DEBUG:
        print("Reading out storage")
    readout_storage()


def storage_read_specific_topic(_topic, _payload, groups):
    read_storage(groups[0].split("/"))


if __name__ == "__main__":
    try:
        print("Starting storage service...")

        load_storage_map()

        pyroslib.subscribe("storage/write/#", storage_write_topic)
        pyroslib.subscribe("storage/read/#", storage_read_specific_topic)
        pyroslib.subscribe("storage/read", storage_read_all_topic)
        pyroslib.init("storage-service")

        print("Started storage service.")

        pyroslib.forever(0.5, priority=pyroslib.PRIORITY_LOW)

    except Exception as ex:
        print("ERROR: " + str(ex) + "\n" + ''.join(traceback.format_tb(ex.__traceback__)))
