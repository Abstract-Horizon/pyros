#!/usr/bin/env python3

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


from local_resources import Resource
from pyros_common import Aliases, Dicscovery
from discovery import DEFAULT_DISCOVERY_TIMEOUT

import argparse
import sys
import os


# discoveryFile = os.path.join(os.environ["HOME"], ".discovery")
# DISCOVERY_TIMEOUT = 60  # one minute


class StartingPyrosCommand:
    def __init__(self):
        self.parser = argparse.ArgumentParser(description='Pyros command line too.')
        # self.parser.add_argument('--help', '-h', type=bool, default=False, help='shows this help')
        self.parser.add_argument('--timeout', '-t', type=int, default=DEFAULT_DISCOVERY_TIMEOUT, help='timeout')
        self.parser.add_argument('destination', nargs=argparse.OPTIONAL, type=str, help='destination in form of host[:port]')
        self.parser.add_argument('command', type=str, help='pyros command')

        self.parser.add_argument('other', nargs=argparse.REMAINDER)

        self.local_commands = ["alias", "daemon", "discover", "help", "install"]
        self.commandAlias = {
            "kill": "stop",
            "rm": "remove"
        }

        self.host = 'localhost'
        self.port = 1883

    @staticmethod
    def _execute_subcommand(sub_command):
        command_filename = "pyros_" + sub_command + ".py"
        # sys.argv[0] = os.path.join(os.path.dirname(sys.argv[0]), command_filename)

        _globals = {"__name__": sub_command}
        with Resource(command_filename) as command_file:
            code = compile(command_file.read(), command_filename, 'exec')
            sys.exit(exec(code, _globals))

    def _command_exists(self, cmd: str) -> bool:
        if cmd in self.commandAlias:
            cmd = self.commandAlias[cmd]
        try:
            with Resource("pyros_" + cmd + ".py"):
                return True
        except FileNotFoundError as ignore:
            return False

    def _process_destination(self, destination, discovery_timeout=None):
        aliases = Aliases()
        aliases.load()

        if destination is None:
            if aliases.default_alias is None:
                destination = Dicscovery(discovery_timeout=discovery_timeout).discover()
            else:
                destination = aliases.aliases['default']
        elif destination in aliases.aliases:
            destination = aliases.aliases[destination]

        host_port = destination.split(':')
        self.host = host_port[0]

        if len(host_port) > 1:
            try:
                self.port = int(host_port[1])
            except:
                print(f"ERROR: Port in destination string ('{destination}') must be a number. '{host_port[1]}' is not a number.")
                sys.exit(1)

        return f"{self.host}:{self.port}"

    @staticmethod
    def _remove_destination(args, destination):
        for i in range(len(args)):
            if args[i] == destination:
                del args[i]
                return args
        raise IndexError(f"Cannot find destination parameter {destination} in arguments {args}")

    @staticmethod
    def _update_destination(args, old_destination, new_destination):
        for i in range(len(args)):
            if args[i] == old_destination:
                args[i] = new_destination
                return args
        raise IndexError(f"Cannot find destination parameter {old_destination} in arguments {args}")

    @staticmethod
    def _insert_destination(args, destination, command):
        for i in range(len(args)):
            if args[i] == command:
                args.insert(i, destination)
                return args
        raise IndexError(f"Cannot find destination parameter {destination} in arguments {args}")

    def run(self):
        executable = sys.argv[0]
        sys_args = [a for a in sys.argv]
        del sys_args[0]
        parsed_args = self.parser.parse_args(sys_args)

        command = parsed_args.command
        command_in_args = command
        destination = parsed_args.destination

        if destination is None:
            # No destination
            if command not in self.local_commands:
                # No destination for non local command
                if self._command_exists(command):
                    destination = self._process_destination(destination, parsed_args.timeout)
                    if destination is None:
                        print(f"Found command that is relating to remove system while destination argument is not supplied")
                        print("")
                        command = "help"
                    else:
                        sys_args = self._insert_destination(sys_args, destination, command)
                else:
                    print(f"Unknown command {command}")
                    print("")
                    command = "help"

            else:  # Local command withot destination
                pass
        elif destination not in self.local_commands and command in self.local_commands:
            # Local command with destination - wrong
            print(f"Found destination while command is supposed to be local only")
            print("")
            command = "help"
            sys_args = self._remove_destination(sys_args, destination)
        elif destination in self.local_commands:
            # Local command
            command_in_args = destination
            command = destination
            destination = None
        elif not self._command_exists(command):  # Remote command
            print(f"Unknown command {command}")
            print("")
            command = "help"
        else:  # Remote command with destination exists
            old_destination = destination
            destination = self._process_destination(destination)
            sys_args = self._update_destination(sys_args, old_destination, destination)

        sys_args = [executable] + sys_args
        sys_args.remove(command_in_args)

        sys.argv = sys_args

        self._execute_subcommand(command)


StartingPyrosCommand().run()
