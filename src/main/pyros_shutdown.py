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


class PyrosShutdown(CommonCommand):
    def __init__(self):
        super(PyrosShutdown, self).__init__(__name__)

    def execute_command(self, client):
        client.publish("system/shutdown", "secret_message")
        return True

    def process_status(self, line, _pid):
        print("STATUS: " + line)

    def run(self):
        args = self.process_common_args_for_remote_command()

        self.process_global_command("system/shutdown", self.execute_command, self.process_out, self.process_status)


PyrosShutdown().run()
