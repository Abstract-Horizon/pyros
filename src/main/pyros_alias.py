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


import argparse

from pyros_common import Aliases, CommonCommand


class PyrosAlias(CommonCommand):
    def __init__(self):
        super(PyrosAlias, self).__init__(__name__, remote_command=False)

        variants_group = self.parser.add_mutually_exclusive_group()
        variants_group.add_argument("-l", "--list", action='store_true', default=False, help="displays all existing aliases")
        variants_group.add_argument("-d", "--delete", metavar="ALIAS", help="set if yo want to delete an alias")
        variants_group.add_argument("alias", nargs=argparse.OPTIONAL, help="alias name or alias and value in form of alias=value")

    def _list(self, aliases):
        if not aliases.aliases:
            print("No aliases set. Use -h for help")
        for alias in aliases.aliases:
            print(alias + " = " + aliases.aliases[alias])

    def run(self):
        aliases = Aliases()
        aliases.load()

        args = self.process_common_args()
        if args.list:
            self._list(aliases)
        elif args.delete is not None:
            alias = args.delete
            if alias in aliases.aliases:
                print(f"Deleted alias {alias} with value {aliases.aliases[alias]}")
                del aliases.aliases[alias]
                aliases.save()
            else:
                print(f"{alias} is not defined")
        elif args.alias is None:
            self._list(aliases)
        else:
            alias_value = args.alias.split("=")
            if len(alias_value) == 1:
                alias = alias_value[0]
                if alias in aliases.aliases:
                    print(f"{alias}={aliases.aliases[alias]}")
                else:
                    print(f"{alias} is not defined")
            else:
                alias = alias_value[0]
                value = alias_value[1]
                aliases.aliases[alias] = value
                aliases.save()
                print(f"Added alias {alias} with value {value}")


PyrosAlias().run()
