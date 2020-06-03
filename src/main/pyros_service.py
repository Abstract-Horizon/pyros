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


from pyros_common import CommonCommand


class PyrosService(CommonCommand):
    def __init__(self):
        super(PyrosService, self).__init__(__name__)
        self.parser.add_argument("process_id", help="process id. ")
        self.parser.add_argument("command", choices=["make", "unmake", "enable", "disable"],
                                 help="'make': promote process to a service.\n"
                                      "'unmake': remove service attribute from a process.\n"
                                      "'enable': enable auto start of the service.\n"
                                      "'disable': disable auto start of the service.")
        self.process_id = None
        self.command = None

    def execute_command(self, client):
        if self.command == "make":
            client.publish("exec/" + self.process_id, "make-service")
        elif self.command == "unmake":
            client.publish("exec/" + self.process_id, "unmake-service")
        elif self.command == "enable":
            client.publish("exec/" + self.process_id, "enable-service")
        elif self.command == "disable":
            client.publish("exec/" + self.process_id, "disable-service")

        return True

    def process_out(self, line, _pid):
        if line.endswith("\n"):
            line = line[:len(line) - 1]
        print(line)
        return False

    def process_status(self, line, pid):
        if line.startswith("PyROS"):
            print(line)
            return False
        return True

    def run(self):
        args = self.process_common_args_for_remote_command()
        self.process_id = args.process_id
        self.command = args.command

        self.process_command(self.process_id, self.execute_command, self.process_out, self.process_status)


PyrosService().run()
