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

import subprocess
import re


class Interface:
    def __init__(self, name):
        self.name = name
        self.addrs = {}
        self.flags = []

    def __repr__(self):
        return self.name


def get_interfaces():
    def _parse_flags(line, iface):
        pass

    def _parse_line(line, iface):
        line = line.strip()
        if line.startswith('inet'):
            s = re.sub(r'\s+', ' ', line).split(' ')
            i = 0
            while i < len(s) - 1:
                key = s[i]
                value = s[i + 1]
                if value.startswith('0x'):
                    try:
                        v = ("00000000" +value[2:])[-8:]
                        value = ".".join([str(int(v[i:i + 2], 16)) for i in range(0, len(v), 2)])
                    except Exception as ignore:
                        pass
                iface.addrs[key] = value
                i += 2

    def _parse_lines(lines, ifaces):
        current_iface = None

        for line in lines:
            if len(line) > 0 and not line[0].isspace():
                iface_split = line.split(":")
                name = iface_split[0]

                current_iface = Interface(name)
                ifaces[name] = current_iface
                if len(iface_split) > 0:
                    _parse_flags(iface_split[1], current_iface)
            else:
                _parse_line(line, current_iface)

    ifaces = {}

    try:
        process = subprocess.Popen('ifconfig', shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

        retval = process.wait()

        lines = process.stdout.readlines()
        lines = [line.decode('ascii') for line in lines]
        _parse_lines(lines, ifaces)

    except Exception as e:
        pass

    return ifaces


if __name__ == "__main__":
    ifaces = get_interfaces()

    for k, v in ifaces.items():
        if 'inet' in v.addresses:
            print(f"{k}: {v.addresses}")
