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


class PyrosRestart(CommonCommand):
    def __init__(self):
        super(PyrosRestart, self).__init__(__name__)
        self.parser.add_argument("-f", "--tail", action='store_true', default=False, help="'tail' messages out of process")
        self.parser.add_argument("process_id", help="process id. ")
        self.tail = False
        self.had_start = False
        self.process_id = None

    def execute_command(self, client):
        client.publish("exec/" + self.process_id, "restart")
        if self.tail:
            self.timeout_count = 0

        return True

    def process_out(self, line, _pid):
        if line.endswith("\n"):
            line = line[:len(line) - 1]
        if not self.tail:
            return False
        print(line)
        return True

    def process_status(self, line, pid):
        if line.startswith("PyROS: started"):
            self.had_start = True
            if self.tail:
                print("Process " + pid + " is restarted. Showing output:")
            else:
                print("Process " + pid + " is restarted.")
            return self.tail
        elif line.startswith("PyROS: exit"):
            print("Process " + pid + " exited.")
            return not self.had_start
        return True

    def run(self):
        args = self.process_common_args_for_remote_command()
        self.tail = args.tail
        self.process_id = args.process_id

        self.process_command(self.process_id, self.execute_command, self.process_out, self.process_status)


PyrosRestart().run()
