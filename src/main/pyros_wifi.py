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


class PyrosShutdown(CommonCommand):
    def __init__(self):
        super(PyrosShutdown, self).__init__(__name__)
        variants_group = self.parser.add_mutually_exclusive_group()
        variants_group.add_argument("-r", "--read", action="store_true", default=None, help="reads all exiting wifi sids")
        variants_group.add_argument("-w", "--write", metavar="sid_and_password",  help="adds given sid/password")
        variants_group.add_argument("-d", "--delete", metavar="sid", help="removes given sid")

        self.command = None

    def execute_command(self, client):
        client.publish("wifi", self.command)
        return True

    def process_out(self, lines, _pid):
        for line in lines.split("\n"):
            if line == ":end":
                return False

            print(line)
        return True

    def process_status(self, line, _pid):
        print("STATUS: " + line)

    def run(self):
        args = self.process_common_args_for_remote_command()
        if args.delete is not None:
            self.command = "delete " + args.delete
        elif args.write is not None:
            write_sid_and_pass = args.write.split(':')
            if len(write_sid_and_pass) != 2:
                print("ERROR: wifi write commmand must be in '<sid>:<password>' format.")
                sys.exit(1)
            if len(write_sid_and_pass[1]) < 8:
                print("ERROR: wifi write commmand must be in '<sid>:<password>' format where password is at least 8 characters long.")
                sys.exit(1)

            self.command = "write " + args.write

        else:
            self.command = "read"

        self.process_global_command("system/shutdown", self.execute_command, self.process_out, self.process_status)


PyrosShutdown().run()
