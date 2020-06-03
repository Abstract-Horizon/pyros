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
import os
import time
import paho.mqtt.client as mqtt
import socket
import argparse
from pyros_common import utils
from discovery import Discover, DEFAULT_DISCOVERY_TIMEOUT


DEFAULT_TIMEOUT_COUNT = 5  # Default 5 counts
DEFAULT_DISCOVERY_FILE_TIMEOUT = 60  # One minute


DEFAULT_TIMEOUT = 10

debug = False

dot_pyros = os.path.join(os.environ["HOME"], ".pyros")
if not os.path.exists(dot_pyros):
    # noinspection PyBroadException
    try:
        os.makedirs(dot_pyros)
    except Exception:
        pass


uniqueId = str(socket.gethostname()) + "." + str(os.getpid())


class Dicscovery:
    def __init__(self, discovery_timeout=DEFAULT_DISCOVERY_TIMEOUT, discovery_file_timeout=DEFAULT_DISCOVERY_FILE_TIMEOUT):
        self.discovery_file = os.path.join(dot_pyros, ".discovery")
        self.discovery_timeot = discovery_timeout
        self.discovery_file_timeout = discovery_file_timeout
        self.discovered_hosts = []

    def run_discovery(self):
        discover = Discover(self.discovery_timeot)
        responses = discover.discover()
        # Filter out all that do not support PYROS
        self.discovered_hosts = [response for response in responses if "NAME" in response and "IP" in response and "PYROS" in response]

    def discover(self):
        if not os.path.exists(self.discovery_file) or os.path.getmtime(self.discovery_file) + self.discovery_file_timeout < time.time():
            self.run_discovery()

        if len(self.discovered_hosts) == 1:
            return f"{self.discovered_hosts[0]['HOST']}:{self.discovered_hosts[0]['PYROS']}"
        else:
            print("More than one rover is discovered. Please select one by its name.")

        return None


class Aliases:
    def __init__(self):
        self.alias_file = os.path.join(dot_pyros, ".aliases")
        self.default_alias = None
        self.aliases = {}

    def load(self):
        if os.path.exists(self.alias_file):
            with open(self.alias_file, 'rt') as file:
                self.aliases = utils.load_properties(file)

        if "default" in self.aliases:
            self.default_alias = self.aliases["default"]

    def save(self):
        with open(self.alias_file, 'wt') as f:
            f.write("\n".join([k + "=" + v for k, v in self.aliases.items()]) + "\n")


class CommonCommand:
    def __init__(self, name, remote_command=True, timeout_count=DEFAULT_TIMEOUT_COUNT):
        self.parser = argparse.ArgumentParser(description='Pyros command line too.', prog="pyros " + name)
        # self.parser.add_argument('--help', '-h', type=bool, default=False, help='shows this help')
        if remote_command:
            self.parser.add_argument('--timeout', '-t', type=int, default=42, help='timeout')
            self.parser.add_argument('destination', type=str, help='destination')

        # self.parser.add_argument('command', type=str, help='pyros command')

        self.has_help_switch = False
        self.timeout_count = timeout_count

        self.connected = False
        self.host = None
        self.port = 1883
        self.client = None

        self.countdown = None
        self.after_command = False

        self.executable = sys.argv[0]

    def get_timeout(self):
        if self.timeout_count is None:
            return DEFAULT_TIMEOUT

        return self.timeout_count

    def process_common_args_for_remote_command(self):
        args = self.parser.parse_args(sys.argv[1:])

        destination = args.destination

        host_port = destination.split(':')
        self.host = host_port[0]
        if len(host_port) > 1:
            # noinspection PyBroadException
            try:
                self.port = int(host_port[1])
            except Exception:
                print(f"ERROR: Port in destination string ('{destination}') must be a number. '{host_port[1]}' is not a number.")
                sys.exit(1)

        return args

    def process_common_args(self):
        args = self.parser.parse_args(sys.argv[1:])
        return args

    def process_out(self, _line, _pid):
        return False

    def process_status(self, _line, pid):
        return False

    def print_out_command(self, execute_command, process_line, header, footer):
        self.client = mqtt.Client("PyROS." + uniqueId)

        self.connected = False
        self.after_command = False

        def on_connect(c, _data, _flags, rc):
            if rc == 0:
                c.subscribe("system/+/out", 0)
            else:
                print(f"ERROR: Connection returned error result: {rc}")
                sys.exit(rc)

            self.connected = True

        def on_message(_client, _data, msg):
            payload = str(msg.payload, 'utf-8')
            topic = msg.topic

            if self.after_command:
                if topic.endswith("/out"):
                    if payload != "":
                        process_line(payload)
                    else:
                        self.connected = False
                self.countdown = self.get_timeout()

        self.client.on_connect = on_connect
        self.client.on_message = on_message

        try:
            try:
                self.client.connect(self.host, self.port, 60)
            except Exception as e:
                print(f"ERROR: failed to connect to {self.host}:{self.port}; {e}")
                sys.exit(1)

            command_id = uniqueId + str(time.time())

            self.countdown = self.get_timeout()

            while not self.connected:
                self.client.loop(1)
                self.countdown -= 1
                if self.countdown == 0:
                    print("ERROR: reached timeout waiting to connect to {self.host}")
                    sys.exit(1)
                elif self.countdown < 0:
                    self.countdown = 0

            if header is not None:
                print(header)

            self.connected = self, execute_command(self.client, command_id)
            self.after_command = True

            self.countdown = self.get_timeout()

            while self.connected:
                for i in range(0, 50):
                    time.sleep(0.015)
                    self.client.loop(0.005)
                self.countdown -= 1
                if self.countdown == 0:
                    print("ERROR: reached timeout waiting for response")
                    sys.exit(1)
                elif self.countdown < 0:
                    self.countdown = 0

            if footer is not None:
                print(footer)
        except KeyboardInterrupt:
            sys.exit(1)

    def process_command(self, process_id, execute_command, process_out=None, process_status=None):
        process_out = self.process_out if process_out is None else process_out
        process_status = self.process_status if process_status is None else process_status

        self.client = mqtt.Client("PyROS." + uniqueId)

        self.connected = False
        self.after_command = False

        def on_connect(c, _data, _flags, rc):
            if rc == 0:
                c.subscribe(f"exec/{process_id}/out", 0)
                c.subscribe(f"exec/{process_id}/status", 0)
            else:
                print("ERROR: Connection returned error result: {rc}")
                sys.exit(rc)

            self.connected = True

        def on_message(_client, _data, msg):
            payload = str(msg.payload, 'utf-8')
            topic = msg.topic

            if self.after_command:
                if topic.startswith("exec/"):
                    if topic.endswith("/out"):
                        pid = topic[5:len(topic)-4]
                        self.connected = process_out(payload, pid)
                    elif topic.endswith("/status"):
                        pid = topic[5:len(topic)-7]
                        self.connected = process_status(payload, pid)

                self.countdown = self.get_timeout()
            # else:
            #     print("Before command: " + payload)

        self.client.on_connect = on_connect
        self.client.on_message = on_message

        try:
            self.client.connect(self.host, self.port, 60)

            self.countdown = self.get_timeout()

            while not self.connected:
                for i in range(0, 50):
                    time.sleep(0.015)
                    self.client.loop(0.005)
                self.countdown -= 1
                if self.countdown == 0:
                    print("ERROR: reached timeout waiting to connect to {self.host}")
                    sys.exit(1)
                elif self.countdown < 0:
                    self.countdown = 0

            self.connected = execute_command(self.client)
            self.after_command = True

            self.countdown = self.get_timeout()

            while self.connected:
                for i in range(0, 50):
                    time.sleep(0.015)
                    self.client.loop(0.005)
                self.countdown -= 1
                if self.countdown == 0:
                    print("ERROR: reached timeout waiting for response")
                    sys.exit(1)
                elif self.countdown < 0:
                    self.countdown = 0
        except KeyboardInterrupt:
            sys.exit(1)

    def process_global_command(self, topic, execute_command, process_out=None, process_status=None):
        process_out = self.process_out if process_out is None else process_out
        process_status = self.process_status if process_status is None else process_status

        self.client = mqtt.Client("PyROS." + uniqueId)

        self.connected = False
        self.after_command = False

        def on_connect(client, _data, _flags, rc):
            if rc == 0:
                if topic.endswith("#"):
                    client.subscribe(topic, 0)
                elif topic.endswith("!"):
                    client.subscribe(topic[0:len(topic) - 2], 0)
                else:
                    client.subscribe(topic + "/out", 0)
            else:
                print("ERROR: Connection returned error result: {rc}")
                sys.exit(rc)

            self.connected = True

        def on_message(_client, _data, msg):
            payload = str(msg.payload, 'utf-8')
            current_topic = msg.topic

            if self.after_command:
                if current_topic.startswith("exec/"):
                    if current_topic.endswith("/out"):
                        pid = current_topic[5:len(current_topic)-4]
                        self.connected = process_out(payload, pid)
                    elif current_topic.endswith("/status"):
                        pid = current_topic[5:len(current_topic)-7]
                        self.connected = process_status(payload, pid)
                else:
                    self.connected = process_out(payload, current_topic)

                self.countdown = self.get_timeout()
            else:
                print("Before command: " + payload)

        self.client.on_connect = on_connect
        self.client.on_message = on_message

        try:
            self.client.connect(self.host, self.port, 60)

            self.countdown = self.get_timeout()

            while not self.connected:
                for i in range(0, 50):
                    time.sleep(0.015)
                    self.client.loop(0.005)
                self.countdown -= 1
                if self.countdown == 0:
                    print("ERROR: reached timeout waiting to connect to {host}")
                    sys.exit(1)
                elif self.countdown < 0:
                    self.countdown = 0

            self.connected = execute_command(self.client)
            self.after_command = True

            self.countdown = self.timeout_count

            while self.connected:
                for i in range(0, 50):
                    time.sleep(0.015)
                    self.client.loop(0.005)
                self.countdown -= 1
                if self.countdown == 0:
                    print("ERROR: reached timeout waiting for response")
                    sys.exit(1)
                elif self.countdown < 0:
                    self.countdown = 0
        except KeyboardInterrupt:
            sys.exit(1)
