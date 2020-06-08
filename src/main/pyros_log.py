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

import sys

from pyros_common import CommonCommand


class PyrosLog(CommonCommand):
    def __init__(self):
        super(PyrosLog, self).__init__(__name__)
        self.parser.add_argument("-a", "--all", action='store_true', default=False, help="reprint last 1000 log lines")
        self.parser.add_argument("process_id", help="process id. "
                                                    "Argument <processId> can be '%' which will mean all output of all processes. "
                                                    "It cannot be used in conjunction with -a option.")
        self.everything = False
        self.all = False
        self.process_id = None

    def execute_command(self, client):
        if self.everything:
            print("Showing all processes output:")
        else:
            print("Showing process " + self.process_id + " output:")
            if self.all:
                client.publish("exec/" + self.process_id, "logs")
        self.timeout_count = 0
        return True

    def process_out(self, line, _pid):
        if line.endswith("\n"):
            line = line[:len(line) - 1]

        if self.everything:
            print(self.process_id + ": " + line, flush=True)
        else:
            print(line, flush=True)
        return True

    def process_status(self, line, pid):
        if line.startswith("PyROS: exit"):
            print("** Process " + pid + " exited.")
            return self.everything
        return True

    def run(self):
        args = self.process_common_args_for_remote_command()
        self.all = args.all
        self.process_id = args.process_id

        if self.process_id == "%":
            if self.all:
                print("ERROR: Cannot use option -a with % (everything).")
                sys.exit(1)
            self.process_id = "+"
            self.everything = True

        self.process_command(self.process_id, self.execute_command, self.process_out, self.process_status)


PyrosLog().run()
