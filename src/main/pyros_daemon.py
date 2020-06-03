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

import argparse
import sys
import os

from pyros_common import CommonCommand, InstallDaemon
from pyros_core.pyros_core import PyrosDaemon


class PyrosDaemonCommand(CommonCommand):
    def __init__(self):
        super(PyrosDaemonCommand, self).__init__(__name__, remote_command=False)
        self.parser.add_argument("-v", "--verbose", action='store_true', default=False, help="set debuging level to verbose")
        self.parser.add_argument("-vv", "--verbose-more", action='store_true', default=False, help="set debuging level to even more verbose")
        self.parser.add_argument("-vvv", "--verbose-most", action='store_true', default=False, help="set debuging level to the most verbose")
        self.parser.add_argument("-t", "--timeout", help="sets timeout in MQTT operations (connect, read, etc)")
        self.parser.add_argument("-d", "--home-dir", help="sets working directory")
        self.parser.add_argument("-f", "--force", action='store_true', default=None, help="installs daemon and code even if they exist")
        self.parser.add_argument("-i", "--install", action='store_true', default=False, help="installs daemon service at given directory")
        self.parser.add_argument("-u", "--user", help="user to be used to run daemon from systemd service")
        self.parser.add_argument("-g", "--group", help="group to be used when creating initial pyros files")
        self.parser.add_argument("-c", "--cluser_id", help="sets cluster id")
        self.parser.add_argument("host_port", nargs=argparse.OPTIONAL, help="host name and optionally port to run at (in host[:port] format)")

    def run(self):
        args = self.parser.parse_args()

        if args.install:
            force = args.force
            user = args.user
            group = args.group if args.group is not None else args.user
            if user is None:
                from pathlib import Path

                path = Path(sys.argv[0])
                user = path.owner()
                if group is None:
                    group = path.group()

            home_dir = args.home_dir
            if home_dir is None:
                self.parser.error("-d/--home-dir switch is mandatory.")

            home_dir = os.path.abspath(home_dir)

            if not os.path.exists(home_dir):
                print(f"ERROR: '{home_dir} does not exist.")
            else:
                InstallDaemon(home_dir, user, group, force).install()
        else:
            if args.force is not None:
                self.parser.error("ERROR: force argument works only with 'install' command.")
                sys.exit(1)

            print("Running daemon...")

            PyrosDaemon().start("pyros " + __name__, sys.argv[1:])

PyrosDaemonCommand().run()
