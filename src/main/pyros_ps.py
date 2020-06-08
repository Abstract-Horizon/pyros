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


import time

from pyros_common import CommonCommand


class PyrosPS(CommonCommand):
    def __init__(self):
        super(PyrosPS, self).__init__(__name__)

    def process_line(self, line):
        if line.endswith("\n"):
            line = line[:len(line) - 1]

        split = line.split(" ")
        if len(split) >= 5:
            try:
                lenInBytes = int(split[4])
                if lenInBytes >= 2 * 1024 * 1024 * 1024:
                    ll = str(round(lenInBytes / (1024.0 * 1024.0 * 1024.0), 2)) + "GB"
                elif lenInBytes > 2 * 1024 * 1024:
                    ll = str(round(lenInBytes / (1024.0 * 1024.0), 2)) + "MB"
                elif lenInBytes > 2 * 1024:
                    ll = str(round(lenInBytes / 1024.0, 2)) + "KB"
                else:
                    ll = str(lenInBytes) + "B"
                split[4] = ll
            except:
                pass

        if len(split) >= 6:
            try:
                t = float(split[5])
                split[5] = "\"" + time.ctime(t) + "\""
            except:
                pass
        else:
            split.append("")

        if len(split) >= 7:
            try:
                t = float(split[6])
                split[6] = "\"" + time.ctime(t) + "\""
            except:
                pass
        else:
            split.append("")

        # print("split=" + str(split))
        print("{0!s:<20} {1:<18} {2:<15} {3:<7} {4:<10} {5:<15} {6:<15}".format(*split))

    def execute_command(self, client, commandId):
        client.publish("system/" + commandId, "ps")
        return True

    def run(self):
        self.process_common_args_for_remote_command()
        self.print_out_command(self.execute_command, self.process_line,
                               "{0:<20} {1:<18} {2:<15} {3:<7} {4:<10} {5:<15} {6:<15}".format(
                               "name", "type", "status", "rc", "len", "date", "pinged"), "")


PyrosPS().run()
