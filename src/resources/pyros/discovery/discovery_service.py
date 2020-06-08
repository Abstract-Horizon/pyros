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

import os
import socket
import fcntl
import struct
import threading
import subprocess
import traceback

from discovery.interfaces import get_interfaces
from local_resources import Resource


class Discovery:
    def __init__(self, typ):
        self._type = typ
        self._debug = False
        self._receiving_socket = None
        self._thread = None
        self._stop = False
        self._services = {}
        self._callbacks = {}
        self._scan_for_services()

    def _scan_for_services(self):
        root = Resource("/")
        for file in root.list():
            if file.endswith("/"):
                discovery_filename = os.path.join(file, "DISCOVERY.py")
                try:
                    # print(f"Checking if '{discovery_file}' existing... ")
                    with Resource(discovery_filename) as discovery_file:
                        print(f"Running '{discovery_filename}'...")
                        code = discovery_file.read().decode("utf-8")
                        try:
                            _globals = {"discovery": self}
                            exec(compile(code, "DISCOVERY.py", 'exec'), _globals)
                            print(f"Done '{discovery_filename}'.")
                        except Exception as e:
                            print(f"WARNING: while processing '{discovery_filename}': {ex}\n{''.join(traceback.format_tb(ex.__traceback__))}")
                except FileNotFoundError:
                    pass

    def register_service(self, name, value):
        self._services[name] = value

    def deregister_service(self, name):
        del self._services[name]

    def register_dynamic_service(self, name, callback):
        self._callbacks[name] = callback

    def deregiser_dynamic_service(self, name):
        del self._callbacks[name]

    @staticmethod
    def _get_ip_address_from_interface(ifname):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        return socket.inet_ntoa(fcntl.ioctl(s.fileno(), 0x8915, bytearray(struct.pack('256s', bytes(ifname[:15], 'utf-8'))))[20:24])

    @staticmethod
    def _get_hostname():
        hostname = "UNKNOWN"
        if os.path.exists("/etc/hostname"):
            with open("/etc/hostname", "rt") as textFile:
                hostname = textFile.read()
        else:
            # noinspection PyBroadException
            try:
                hostname = subprocess.Popen('hostname', shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT) \
                    .stdout.readlines()[0].decode('ascii')
            except Exception:
                pass

        hostname = hostname.split(".")[0].replace('\n', '')
        if hostname.startswith("gcc-"):
            hostname = hostname[4].upper() + hostname[5:]
            hostname = hostname.replace("-", "")

        return hostname

    @staticmethod
    def _get_ip_address(client_ip):
        client_ip = client_ip.split('.')

        def _calc_weight(ip1):
            j = 0
            while j < len(ip1) and j < len(client_ip) and ip1[j] == client_ip[j]:
                j += 1
            return j

        all_ips = [iface.addrs['inet'].split('.') for iface in get_interfaces().values() if 'inet' in iface.addrs and 'broadcast' in iface.addrs]
        ip_weights = {".".join(ip): _calc_weight(ip) for ip in all_ips}

        return max(ip_weights, key=lambda k: ip_weights[k])

    def _prepare_response(self, client_ip):
        response_map = {
            "IP": self._get_ip_address(client_ip),
            "NAME": self._get_hostname(),
            "TYPE": self._type}

        for service_name in self._services:
            response_map[service_name] = self._services[service_name]

        for callback_name in self._callbacks:
            callback = self._callbacks[callback_name]
            callback(response_map)

        return "A#" + ";".join([k + "=" + v for k, v in response_map.items()])

    def _receive(self):
        self._receiving_socket.settimeout(10)
        if self._debug:
            print("    Started receive thread...")
        while not self._stop:
            # noinspection PyBroadException
            try:
                data, addr = self._receiving_socket.recvfrom(1024)
                request = str(data, 'utf-8')

                if self._debug:
                    print("Received: " + str(request))

                if request.startswith("Q#"):
                    p = {kv[0].strip(): kv[1].strip() for kv in [line.split("=") for line in [entry.replace('\n', '') for entry in request[2:].split(';')]]}

                    return_ip = p["IP"]
                    # noinspection PyBroadException
                    try:
                        return_port = int(p["PORT"])
                    except Exception:
                        return_port = 0xd15c

                    response = self._prepare_response(return_ip)

                    self._send(return_ip, return_port, response)
            # except Exception as ex:
            #     print("ERROR: " + str(ex) + "\n" + ''.join(traceback.format_tb(ex.__traceback__)))
            except Exception:
                pass

    def _send(self, ip, port, packet):
        if self._debug:
            print("Debug: sending packet to " + str(ip) + ":" + str(port) + " " + packet)

        sending_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sending_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sending_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sending_socket.setblocking(False)

        sending_socket.sendto(bytes(packet, 'utf-8'), (ip, port))

    def start(self):
        self._stop = False
        self._receiving_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._receiving_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._receiving_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self._receiving_socket.bind(('', 0xd15c))

        self._thread = threading.Thread(target=self._receive, args=())
        self._thread.daemon = True
        self._thread.start()

    def stop(self):
        self._stop = True


if __name__ == "__main__":
    try:
        import pyroslib

        print("Starting discovery service...")

        pyroslib.init("discovery-service")

        discovery_service = Discovery("PYROS")
        # discovery_service._debug = True
        discovery_service.start()

        print("Started discovery service.")

        pyroslib.forever(0.5, priority=pyroslib.PRIORITY_LOW)

    except Exception as ex:
        print("ERROR: " + str(ex) + "\n" + ''.join(traceback.format_tb(ex.__traceback__)))
