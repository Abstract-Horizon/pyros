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


class PyrosStop(CommonCommand):
    def __init__(self):
        super(PyrosStop, self).__init__(__name__)

        variants_group = self.parser.add_mutually_exclusive_group()
        read_group = variants_group.add_argument_group()
        read_group.add_argument("read", choices=["read"], help="reads storage from given path")
        read_group.add_argument("read_path")
        write_group = variants_group.add_argument_group()
        write_group.add_argument("write", choices=["write"], help="writes to storage on given path")
        write_group.add_argument("write_path")
        write_group.add_argument("write_value")
        delete_group = variants_group.add_argument_group()
        delete_group.add_argument("delete", choices=["delete", "del"], help="deletes entry at given path")
        delete_group.add_argument("delete_path")

        self.timeout_count = 5  # Default timeout 5 seconds
        self.command = "read"
        self.path = ""
        self.value = ""

    def execute_command(self, client):
        if self.command == "read":
            if self.path == "/":
                client.publish("storage/read", self.command)
            else:
                client.publish("storage/read/" + self.path, self.command)
        elif self.command == "delete":
            client.publish("storage/write/" + self.path, "")
            print("Deleting on path: '" + self.path + "'")
        elif self.command == "write":
            client.publish("storage/write/" + self.path, self.value)
        return True

    def process_out(self, line, _pid):
        if self.path.startswith("storage/write/"):
            self.path = self.path[14:]
        print(self.path + " = " + line)

    def process_status(self, line, pid):
        print(line)

    def run(self):
        args = self.process_common_args_for_remote_command()
        if args.delete is not None:
            self.command = "delete"
            self.path = args.delete_path
        elif args.write is not None:
            self.command = "write"
            self.path = args.write_path
            self.value = args.write_value
        else:
            self.command = "read"
            self.path = args.read_path

        self.process_global_command("storage/write/#", self.execute_command, self.process_out, self.process_status)


PyrosStop().run()
