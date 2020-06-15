################################################################################
# Copyright (C)2020 Abstract Horizon
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
import traceback

from discovery import Discovery
from local_resources import Resource


def _scan_for_services(discovery_service):
    root = Resource("/")
    for file in root.list():
        if file.endswith("/"):
            discovery_filename = os.path.join(file, "DISCOVERY.py")
            try:
                # print(f"Checking if '{discovery_file}' existing... ")
                with Resource(discovery_filename) as discovery_file:
                    print(f"Running '{discovery_filename}'...")
                    code = discovery_file.read().decode("utf-8")
                    # noinspection PyBroadException
                    try:
                        _globals = {"discovery": discovery_service}
                        exec(compile(code, "DISCOVERY.py", 'exec'), _globals)
                        print(f"Done '{discovery_filename}'.")
                    except Exception as ex:
                        print(f"WARNING: while processing '{discovery_filename}': {ex}\n{''.join(traceback.format_tb(ex.__traceback__))}")
            except FileNotFoundError:
                pass


if __name__ == "__main__":
    try:
        import pyroslib

        print("Starting discovery service...")
        pyroslib.init("discovery-service")
        discovery_service = Discovery("PYROS")
        # discovery_service._debug = True
        discovery_service.start()
        _scan_for_services(discovery_service)
        print("Started discovery service.")

        pyroslib.forever(0.5, priority=pyroslib.PRIORITY_LOW)
    except Exception as ex:
        print("ERROR: " + str(ex) + "\n" + ''.join(traceback.format_tb(ex.__traceback__)))