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


class PyrosRemove(CommonCommand):
    def __init__(self):
        super(PyrosRemove, self).__init__(__name__)
        self.parser.add_argument("process_id", help="process id. ")
        self.process_id = None

    def execute_command(self, client):
        client.publish("exec/" + self.process_id, "remove")
        return False

    def run(self):
        args = self.process_common_args_for_remote_command()
        self.process_id = args.process_id

        self.process_command(self.process_id, self.execute_command)


PyrosRemove().run()
