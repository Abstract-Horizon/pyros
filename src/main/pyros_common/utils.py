################################################################################
# Copyright (C) 2016-2020 Abstract Horizon
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License v2.0
# which accompanies this distribution, and is available at
# https://www.apache.org/licenses/LICENSE-2.0
#
#  Contributors:
#    Daniel Sendula - initial API and implementation
#
#################################################################################


import os
import zipfile
from local_resources import Resource


def ensure_dir(this_path, user, group, path, verbose=True):
    dir = os.path.join(this_path, path)
    if not os.path.exists(dir):
        if verbose:
            print("Creating: " + dir)
        os.makedirs(dir)
        chown_cmd = "chown " + user + ":" + group + " " + dir
        if verbose:
            print("Running: " + chown_cmd)
        os.system(chown_cmd)
        return False
    else:
        return True


def load_properties(file):
    return {kv[0].strip(): kv[1].strip()
            for kv in [line.split("=") for line in [l.replace('\n', '') for l in file.readlines()]]
            if len(kv) == 2 and not kv[0].lstrip().startswith('#')}


def read_this_version():
    try:
        with Resource("VERSION") as f:
            return f.readline().decode('ascii').replace('\n', '')
    except FileNotFoundError as ignore:
        return ""


def read_other_version(file):
    try:
        zip_file = zipfile.ZipFile(file)
        with zip_file.open("VERSION") as f:
            return f.readline().decode('ascii').replace('\n', '')
    except FileNotFoundError as ignore:
        return ""