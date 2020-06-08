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


from discovery import Discover, DEFAULT_DISCOVERY_TIMEOUT
from pyros_common import CommonCommand


class PyrosDiscover(CommonCommand):
    def __init__(self):
        super(PyrosDiscover, self).__init__(__name__, remote_command=False)

        self.parser.add_argument("-v", "--verbose", action='store_true', default=False, help="set debuging level to verbose")
        self.parser.add_argument("-t", "--timeout", type=int, default=DEFAULT_DISCOVERY_TIMEOUT, help="sets timeout, default is " + str(DEFAULT_DISCOVERY_TIMEOUT))

    def run(self):
        args = self.process_common_args()

        discover = Discover(args.timeout, debug=args.verbose)
        response = discover.discover()
        print("")
        for details in response:
            print(str(details)[1:-1])

PyrosDiscover().run()
