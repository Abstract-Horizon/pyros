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
import sys
import pyros_common.utils as utils

from pyros_common import CommonCommand, InstallDaemon


class PyrosInstall(CommonCommand):
    def __init__(self):
        super(PyrosInstall, self).__init__(__name__, remote_command=False)
        self.parser.add_argument("command", choices=["daemon", "command"])
        self.parser.add_argument("-f", "--force", action="store_true", default=False, help="installs daemon or command even if one exists")
        self.parser.add_argument("-u", "--user", help="user to be used to run daemon from systemd service")
        self.parser.add_argument("-g", "--group", help="group to be used when creating initial pyros files")
        self.parser.add_argument("-d", "--home-dir", help="installs daemon service at given directory")

    @staticmethod
    def _list(aliases):
        if not aliases.aliases:
            print("No aliases set. Use -h for help")
        for alias in aliases.aliases:
            print(alias + " = " + aliases.aliases[alias])

    def run(self):
        args = self.process_common_args()

        if args.command == "daemon":
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
                self.parser.error(f"ERROR: '{home_dir} does not exist.")
            else:
                force = args.force if args.force is not None else False
                InstallDaemon(home_dir, user, group, force).install()

        elif args.command == "command":
            this_file = sys.argv[0]
            if os.path.isdir(this_file):
                self.parser.error("ERROR: install only works with packaged version of pyros")
            else:
                if not os.path.exists("/usr/local/bin"):
                    self.parser.error("ERROR: cannot find /usr/local/bin")
                else:
                    this_version = utils.read_this_version()
                    other_version = utils.read_other_version('/usr/local/bin/pyros')

                    if this_version <= other_version and not args.force:
                        print(f"ERROR: this pyros version is {this_version} while installed is newer {other_version}. If you want to proceed use --force switch.")
                    else:
                        if other_version != "":
                            if this_version < other_version:
                                print(f"Warning: Installing older version {this_version} over newer {other_version}")
                            elif this_version > other_version:
                                print(f"Installing newer version {this_version} over older {other_version}")
                        print(f"Copying {this_file} to /usr/local/bin/pyros")
                        with open(this_file, "rb") as in_file:
                            # noinspection PyBroadException
                            try:
                                with open("/usr/local/bin/pyros", "wb") as out_file:
                                    out_file.write(in_file.read())
                            except Exception:
                                self.parser.error("ERROR: Cannot copy to '/usr/local/bin/pyros'. Maybe to run with sudo?")
                        os.system("chmod a+x /usr/local/bin/pyros")

PyrosInstall().run()
