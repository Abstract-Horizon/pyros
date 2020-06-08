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

import traceback
from discovery.discovery_service import Discovery

if __name__ == "__main__":
    try:
        import pyroslib

        print("Starting discovery service...")

        pyroslib.init("discovery-service")

        discovery_service = Discovery("PYROS")
        # discovery_service._debug = True
        discovery_service.start()

        print("Started discovery service.")

        pyroslib.forever(0.5, priority=pyroslib.PRIORITY_LOW)

    except Exception as ex:
        print("ERROR: " + str(ex) + "\n" + ''.join(traceback.format_tb(ex.__traceback__)))
