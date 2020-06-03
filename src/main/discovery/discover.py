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

import socket
import threading
import time
# import netifaces
from discovery.interfaces import get_interfaces


DEFAULT_DISCOVERY_TIMEOUT = 5


class Discover:
    def __init__(self, discovery_timeout, debug=False):
        self._debug = debug
        self._discovery_timeout = discovery_timeout
        self._discovery_sockets = []
        self._responses = []

        ifaces = get_interfaces()

        if self._debug:
            print("  Discovered network adapters:")

        for iface_name in ifaces:
            iface = ifaces[iface_name]
            if 'inet' in iface.addrs and 'broadcast' in iface.addrs and iface.addrs['inet'] != '127.0.0.1':
                my_ip = iface.addrs['inet']
                broadcast_ip = iface.addrs['broadcast']

                sending_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                sending_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                sending_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                sending_socket.setblocking(False)
                sending_socket.settimeout(self._discovery_timeout)

                listening_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                listening_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                listening_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                listening_socket.setblocking(False)
                listening_socket.settimeout(self._discovery_timeout)

                listening_socket.bind((my_ip, 0))

                self._discovery_sockets.append((my_ip, broadcast_ip, sending_socket, listening_socket))

                if self._debug:
                    print("    " + str(broadcast_ip))

    @staticmethod
    def _apply_netmask(ip, netmask, value):
        ip_a = ip.split('.')
        netmask_a = netmask.split('.')
        for i in range(0, 4):
            if netmask_a[i] != '255':
                ip_a[i] = value

        return ".".join(ip_a)

    def send_discovery_packet(self, packet):
        for i in range(0, len(self._discovery_sockets)):
            my_ip, broadcast_ip, sending_socket, listening_socket = self._discovery_sockets[i]

            updated_packet = packet + "IP=" + my_ip + ";PORT=" + str(listening_socket.getsockname()[1])
            sending_socket.sendto(bytes(updated_packet, 'utf-8'), (broadcast_ip, 0xd15c))
            if self._debug:
                print("  send discovery packet to " + str(broadcast_ip) + ":0xd15c, packet=" + str(updated_packet))

    def _process_response(self, response_to_processs):
        parsed_response = {kv[0]: kv[1] for kv in [kv for kv in [kv.split('=') for kv in response_to_processs.split(';')] if len(kv) > 1]}
        parsed_response.update({kv[0]: None for kv in [kv for kv in [kv.split('=') for kv in response_to_processs.split(';')] if len(kv) == 1]})
        # parsed_response.update({"ERROR_" + str(i + 1): kv[0] for i, kv in enumerate([kv for kv in [kv.split('=') for kv in response_to_processs.split(';')] if len(kv) == 1])})

        self._responses.append(parsed_response)

    def _receive_discovery_packets(self, listening_socket):
        start_time = time.time()
        if self._debug:
            print("  receiving at " + str(listening_socket.getsockname()))
        while time.time() - start_time < self._discovery_timeout:
            # noinspection PyBroadException
            try:
                data, addr = listening_socket.recvfrom(1024)
                p = str(data, 'utf-8')
                if self._debug:
                    print("  received " + p)

                if p.startswith("A#"):
                    self._process_response(p[2:])
                # elif p.startswith("Q#"):
                #     print("Received self query:" + p)
            except Exception:
                pass

    def discover(self):
        del self._responses[:]
        for my_ip, broadcast_ip, sending_socket, listening_socket in self._discovery_sockets:
            thread = threading.Thread(target=self._receive_discovery_packets, args=(listening_socket,))
            thread.daemon = False
            thread.start()

        time.sleep(1)
        self.send_discovery_packet("Q#")

        time.sleep(self._discovery_timeout + 0.5)

        return self._responses


if __name__ == "__main__":
    discover = Discover(10)
    response = discover.discover()
    print("")
    print("{0!s:<20} {1:<20} {2:<20} {3}".format("ip", "name", "type", "other"))
    for details in response:
        # print("{0!s:<20} {1:<20} {2:<20} {3}".format(details["IP"] + ":" + details["PORT"], details["NAME"], details["TYPE"], ";".join(errors)))
        # print("{0!s:<20} {1:<20} {2:<20} {3}".format(details["IP"] + ":" + details["PORT"] if "PORT" in details else "", details["NAME"], details["TYPE"], ""))
        print(str(details))
