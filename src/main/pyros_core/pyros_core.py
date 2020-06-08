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

import argparse
import os
import sys
import time
import subprocess
import threading
import traceback

import paho.mqtt.client as mqtt

from queue import Queue, Empty
from concurrent.futures import ThreadPoolExecutor
from typing import Dict


DEFAULT_TIMEOUT = 60
DEFAULT_RECONNECT_RETRIES = 20  # number of reconnect timeouts before process exits

DEFAULT_THREAD_KILL_TIMEOUT = 1.0

DEFAULT_AGENTS_CHECK_TIMEOUT = 1.0
DEFAULT_AGENT_KILL_TIMEOT = 180
DEFAULT_DEBUG_LEVEL = 1


class PyrosDaemon:
    def __init__(self):
        self.do_exit = False
        self.home_dir = os.path.abspath(os.getcwd())
        self.thread_kill_timeout = DEFAULT_THREAD_KILL_TIMEOUT
        self.agents_check_timeout = DEFAULT_AGENTS_CHECK_TIMEOUT
        self.agents_kill_timeout = DEFAULT_AGENT_KILL_TIMEOT
        self.debug_level = DEFAULT_DEBUG_LEVEL
        self.code_dir_name = "code"
        self.host = "localhost"
        self.port = 1883
        self.timeout = DEFAULT_TIMEOUT
        self.max_reconnect_retries = DEFAULT_RECONNECT_RETRIES
        self.this_cluster_id = None
        self.client = None
        self.processes = {}

    @staticmethod
    def important(line):
        print(line)

    def info(self, line):
        if self.debug_level > 0:
            print(line)

    def debug(self, line):
        if self.debug_level > 1:
            print(line)
    
    def trace(self, line):
        if self.debug_level > 2:
            print(line)

    def process_configuration(self, name, arguments):
        def read_config_str(cfg, property_name, default):
            return cfg[property_name] if property_name in cfg else default

        def read_config_int(cfg, property_name, default):
            if property_name in cfg:
                # noinspection PyBroadException
                try:
                    return int(cfg[property_name])
                except Exception:
                    print(f"  error: cannot convert '{property_name}' to integer; got '{cfg[property_name]}'")
            return default

        def read_config_float(cfg, property_name, default):
            if property_name in cfg:
                # noinspection PyBroadException
                try:
                    return float(cfg[property_name])
                except Exception:
                    print(f"  error: cannot convert '{property_name}' to float; got '{cfg[property_name]}'")
            return default

        parser = argparse.ArgumentParser(description='Pyros core daemon.', prog=name)
        parser.add_argument("-v", "--verbose", action='store_true', default=False, help="set debuging level to verbose")
        parser.add_argument("-vv", "--verbose-more", action='store_true', default=False, help="set debuging level to even more verbose")
        parser.add_argument("-vvv", "--verbose-most", action='store_true', default=False, help="set debuging level to the most verbose")
        parser.add_argument("-t", "--timeout", type=int, default=DEFAULT_TIMEOUT, help="sets timeout in MQTT operations (connect, read, etc)")
        parser.add_argument("-d", "--home-dir", help="sets working directory")
        parser.add_argument("-c", "--cluser_id", help="sets cluster id")
        parser.add_argument("host_port", nargs=argparse.OPTIONAL, help="host name and optionally port to run at (in host[:port] format)")

        parsed_args = parser.parse_args(arguments)

        if parsed_args.home_dir is not None:
            self.home_dir = os.path.abspath(parsed_args.home_dir)
            if not os.path.exists(self.home_dir):
                raise FileNotFoundError(f"Home directory {self.home_dir} does not exist.")

        with open(os.path.join(self.home_dir, "pyros.config"), 'r') as config_file:
            config = {kv[0].strip(): kv[1].strip()
                      for kv in [line.split("=") for line in [line.replace('\n', '') for line in config_file.readlines()]]
                      if len(kv) == 2 and not kv[0].lstrip().startswith('#')}

        self.debug_level = read_config_int(config, 'debug.level', self.debug_level)

        if parsed_args.verbose_most:
            self.debug_level = 3
        elif parsed_args.verbose_more:
            self.debug_level = 2
        elif parsed_args.verbose:
            self.debug_level = 1

        self.timeout = read_config_int(config, 'mqtt.timeout', parsed_args.timeout)

        self.host = read_config_str(config, 'mqtt.host', self.host)
        self.port = read_config_str(config, 'mqtt.port', self.port)

        if parsed_args.host_port is not None:
            host_port = parsed_args.host_port.split(':')
            if len(host_port) > 1:
                self.host = host_port[0]
                # noinspection PyBroadException
                try:
                    self.port = int(host_port[1])
                except Exception:
                    self.important(f"ERROR: self.port must be a number. '{host_port[1]}' is not a number.")
                    sys.exit(1)
            else:
                self.host = host_port

        if 'PYROS_MQTT' in os.environ:
            host_str = os.environ['PYROS_MQTT']
            host_split = host_str.split(":")
            if len(host_split) == 1:
                self.host = host_split[0]
            elif len(host_split) == 2:
                self.host = host_split[0]
                # noinspection PyBroadException
                try:
                    self.port = int(host_split[1])
                except Exception:
                    self.important(f"ERROR: self.port must be a number. '{host_split[1]}' is not a number.")
                    sys.exit(1)
            else:
                self.important(f"ERROR: self.host and self.port should in self.host:self.port format not '{host_str}'.")
                sys.exit(1)

        self.max_reconnect_retries = read_config_int(config, 'mqtt.max_reconnect_retries', self.max_reconnect_retries)

        self.this_cluster_id = read_config_int(config, 'cluster_id', self.this_cluster_id)

        if 'PYROS_CLUSTER_ID' in os.environ:
            self.this_cluster_id = os.environ['PYROS_CLUSTER_ID']

        self.agents_kill_timeout = read_config_int(config, 'agents.kill.timeout', self.agents_kill_timeout)
        self.agents_check_timeout = read_config_float(config, 'agents.check.timeout', self.agents_check_timeout)
        self.thread_kill_timeout = read_config_float(config, 'thread.kill.timeout', self.thread_kill_timeout)

    def complex_process_id(self, process_id: str) -> str:
        if self.this_cluster_id is not None:
            return self.this_cluster_id + ":" + process_id
        return process_id

    def process_dir(self, process_id: str) -> str:
        return os.path.join(self.code_dir_name, process_id)

    def process_filename(self, process_id: str) -> str:
        return os.path.join(self.process_dir(process_id), process_id + "_main.py")

    def process_init_filename(self, process_id: str) -> str:
        return os.path.join(self.process_dir(process_id), "__init__.py")

    def process_service_filename(self, process_id: str) -> str:
        old_service_filename = os.path.join(self.process_dir(process_id), ".service")
        process_config_filename = os.path.join(self.process_dir(process_id), ".process")
    
        # convert from old .service files to .process file
        if os.path.exists(old_service_filename):
            os.rename(old_service_filename, process_config_filename)
    
        return process_config_filename

    def make_process_dir(self, process_id: str) -> None:
        if not os.path.exists(self.code_dir_name):
            os.mkdir(self.code_dir_name)

        if not os.path.exists(self.process_dir(process_id)):
            os.mkdir(self.process_dir(process_id))

    def load_service_file(self, process_id: str) -> Dict[str, str]:
        properties = {}
        service_file = self.process_service_filename(process_id)
        if os.path.exists(service_file):
            with open(service_file, 'rt') as f:
                lines = f.read().splitlines()
            for line in lines:
                if not line.strip().startswith("#"):
                    split = line.split('=')
                    if len(split) == 2:
                        properties[split[0].strip()] = split[1].strip()
        return properties

    def save_service_file(self, process_id, properties):
        def _line(t):
            return t[0] + "=" + t[1]

        service_file = os.path.join(self.process_dir(process_id), ".process")

        lines = "\n".join(list(map(_line, list(properties.items())))) + "\n"
        with open(service_file, 'wt') as f:
            f.write(lines)

    def is_running(self, process_id: str) -> bool:
        if process_id in self.processes:
            process = self.get_process_process(process_id)
            if process is not None:
                return_code = process.returncode
                if return_code is None:
                    return True
    
        return False

    def _output(self, process_id, line):
        line = line[:-1] if  line.endswith("\n") else line

        self.client.publish("exec/" + self.complex_process_id(process_id) + "/out", line)
        if self.debug_level > 2:
            self.trace("exec/" + self.complex_process_id(process_id) + "/out > " + line)

    def output(self, process_id, line):
        if "logs" not in self.processes[process_id]:
            logs = []
            self.processes[process_id]["logs"] = logs
        else:
            logs = self.processes[process_id]["logs"]
    
        if len(logs) > 1000:
            del logs[0]
    
        logs.append(line)
        self._output(process_id, line)
    
    def output_status(self, process_id, status):
        self.client.publish("exec/" + self.complex_process_id(process_id) + "/status", status)
        if self.debug_level > 2:
            self.trace("exec/" + self.complex_process_id(process_id) + "/status > " + status)

    def system_output(self, command_id, line):
        self.client.publish("system/" + command_id + "/out", line + "\n")
        if self.debug_level > 2:
            if line.endswith("\n"):
                self.trace("system/" + command_id + "/out > " + line[:len(line) - 1])
            else:
                self.trace("system/" + command_id + "/out > " + line)
    
    def system_output_eof(self, command_id):
        self.client.publish("system/" + command_id + "/out", "")

    def is_service(self, process_id: str) -> str:
        return process_id in self.processes and self.processes[process_id]["type"] == "service"
    
    def is_agent(self, process_id: str) -> str:
        return process_id in self.processes and self.processes[process_id]["type"] == "agent"

    def run_process(self, process_id: str) -> None:
        def _enqueue_output(file, queue):
            for _line in iter(file.readline, ''):
                queue.put(_line)
            file.close()

        def _read_popen_pipes(p):
            with ThreadPoolExecutor(2) as pool:
                q_stdout, q_stderr = Queue(), Queue()

                pool.submit(_enqueue_output, p.stdout, q_stdout)
                pool.submit(_enqueue_output, p.stderr, q_stderr)

                while True:
                    if p.poll() is not None and q_stdout.empty() and q_stderr.empty():
                        break

                    try:
                        stdout_line = q_stdout.get_nowait()
                    except Empty:
                        stdout_line = ""

                    try:
                        strerr_line = q_stderr.get_nowait()
                    except Empty:
                        strerr_line = ""

                    yield stdout_line, strerr_line

        time.sleep(0.25)
        process_is_service = self.is_service(process_id)
    
        if process_is_service:
            self.info("Starting new service " + process_id)
        else:
            self.info("Starting new process " + process_id)
    
        filename = self.process_filename(process_id)
        try:
            subprocess_dir = os.path.join(self.home_dir, os.path.dirname(filename))
            self.debug("Starting " + filename + " at dir " + subprocess_dir)
    
            new_env = os.environ.copy()
            if "PYTHONPATH" in new_env:
                new_env["PYTHONPATH"] = new_env["PYTHONPATH"] + ":" + os.path.join(self.home_dir, "code")
            else:
                new_env["PYTHONPATH"] = os.path.join(self.home_dir, "code")

            new_env["PYROS_MQTT"] = self.host + ":" + str(self.port)
            process_def = self.processes[process_id]
    
            if "exec" in process_def:
                executable = process_def["exec"]
            else:
                executable = "python3"
    
            if executable.startswith("python"):
                command = [executable, "-u", process_id + "_main.py", process_id]
            else:
                command = [executable, "-u", process_id, process_id]

            if self.debug_level > 2:
                python_path = "    " + "\n    ".join(new_env['PYTHONPATH'].split(':')) + "\n"
                self.trace(f"Starting {command} with PYTHONPATH:\n{python_path}")
            elif self.debug_level > 1:
                self.debug(f"Starting {command}")

            process = subprocess.Popen(command,
                                       env=new_env,
                                       bufsize=0,
                                       stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE,
                                       shell=False,
                                       universal_newlines=True,
                                       cwd=subprocess_dir)
            self.output_status(process_id, "PyROS: started process.")
        except Exception as exception:
            self.important("Start file " + filename + " (" + os.path.abspath(filename) + ") failed; " + str(exception))
            self.output_status(process_id, "PyROS: exit.")
            return
    
        self.processes[process_id]["process"] = process
        if "old" in self.processes[process_id]:
            del self.processes[process_id]["old"]

        # pid = process.pid

        process.poll()

        return_code = process.returncode
        while return_code is None:
            for out_line, err_line in _read_popen_pipes(process):
                if err_line is not None and err_line != "":
                    self.output(process_id, err_line)
                if out_line is not None and out_line != "":
                    self.output(process_id, out_line)
                # print(out_line, end='')
                # print(err_line, end='')
                if out_line == "" and err_line == "":
                    time.sleep(0.25)
            return_code = process.poll()

        # noinspection PyBroadException
        try:
            for line in process.stdout.readlines():
                if len(line) > 0:
                    self.output(process_id, line)
        except Exception:
            pass

        # noinspection PyBroadException
        try:
            for line in process.stderr.readlines():
                if len(line) > 0:
                    self.output(process_id, line)
        except Exception:
            pass

        self.output_status(process_id, "PyROS: exit " + str(process.returncode))

    def get_process_type_name(self, process_id: str) -> str:
        if self.is_service(process_id):
            if "enabled" in self.processes[process_id] and self.processes[process_id]["enabled"] == "True":
                return "service"
            else:
                return "service(disabled)"
        elif self.is_agent(process_id):
            return "agent"
        elif "type" in self.processes[process_id]:
            return self.processes[process_id]["type"]
        else:
            return "process"

    def get_process_process(self, process_id: str):
        if process_id in self.processes:
            if "process" in self.processes[process_id]:
                return self.processes[process_id]["process"]
    
        return None

    def start_process(self, process_id: str) -> None:
        if process_id in self.processes:
            process = self.get_process_process(process_id)
            if process is not None:
                return_code = process.returncode
                if return_code is None:
                    self.output(process_id, "PyrROS WARNING: process " + process_id + " is already running")
                    return

            thread = threading.Thread(target=self.run_process, args=(process_id,), daemon=True)
            thread.start()
        else:
            self.output(process_id, "PyROS ERROR: process " + process_id + " does not exist.")

    @staticmethod
    def _sanitise_filename(process_id, filename):
        remove_len = len("code/" + process_id + "/")
        if len(filename) <= remove_len:
            return filename

        return filename[remove_len:]

    def store_code(self, process_id, payload):
        if process_id in self.processes:
            self.processes[process_id]["old"] = True
    
        self.make_process_dir(process_id)
    
        if process_id not in self.processes:
            self.processes[process_id] = {}
    
        if "type" not in self.processes[process_id]:
            self.processes[process_id]["type"] = "process"
    
        if "exec" not in self.processes[process_id]:
            self.processes[process_id]["exec"] = "python3"
    
        filename = self.process_filename(process_id)
        init_filename = self.process_init_filename(process_id)

        # noinspection PyBroadException
        try:
            with open(filename, "wt") as textFile:
                textFile.write(payload)
            with open(init_filename, "wt") as textFile:
                textFile.write("from " + process_id + "." + process_id + "_main import *\n")
    
            self.output_status(process_id, "stored " + self._sanitise_filename(process_id, filename))
        except Exception:
            self.important("ERROR: Cannot save file " + filename + " (" + os.path.abspath(filename) + "); ")
            self.output_status(process_id, "store error")

    def store_extra_code(self, process_id, name, payload):
        self.make_process_dir(process_id)
    
        filename = os.path.join(self.process_dir(process_id), name)
    
        filedir = os.path.dirname(filename)
        print("  making file dir " + str(filedir))
        os.makedirs(filedir, exist_ok=True)
    
        print("  storing extra file " + str(filename))

        # noinspection PyBroadException
        try:
            with open(filename, "wb") as textFile:
                textFile.write(payload)
    
            self.output_status(process_id, "stored " + self._sanitise_filename(process_id, filename))
        except Exception:
            self.important("ERROR: Cannot save file " + filename + " (" + os.path.abspath(filename) + "); ")
            self.output_status(process_id, "store error")

    def stop_process(self, process_id, restart=False):
    
        def start_it_again(process_id_to_start):
            self.start_process(process_id_to_start)
            if self.is_service(process_id_to_start):
                self.output(process_id_to_start, "PyROS: Restarted service " + process_id_to_start)
            else:
                self.output(process_id_to_start, "PyROS: Restarted process " + process_id_to_start)
    
        def final_process_kill(process_id_to_kill):
            time.sleep(0.01)
            # Just in case - we really need that process killed!!!
            cmd_and_args = ["/usr/bin/pkill -9 -f 'python3 -u " + process_id_to_kill + ".py " + process_id_to_kill + "'"]
            res = subprocess.call(cmd_and_args, shell=True)
            if res != -9 and res != 0:
                self.info("Tried to kill " + process_id_to_kill + " but got result " + str(res) + "; command: " + str(cmd_and_args))
            if restart:
                start_it_again(process_id_to_kill)
    
        def wait_for_process_stop(process_id_stop):
            _now = time.time()
            while time.time() - _now < self.thread_kill_timeout and 'stop_response' not in self.processes[process_id_stop]:
                time.sleep(0.05)
    
            _process = self.get_process_process(process_id_stop)
            if 'stop_response' in self.processes[process_id_stop]:
                del self.processes[process_id_stop]['stop_response']
                while time.time() - _now < self.thread_kill_timeout and _process.returncode is None:
                    time.sleep(0.05)
                if _process.returncode is None:
                    _process.kill()
                    self.info("PyROS: responded with stopping but didn't stop. Killed now " + self.get_process_type_name(process_id_stop))
                    self.output(process_id_stop, "PyROS: responded with stopping but didn't stop. Killed now " + self.get_process_type_name(process_id_stop))
                else:
                    self.info("PyROS: stopped " + self.get_process_type_name(process_id_stop))
                    self.output(process_id_stop, "PyROS: stopped " + self.get_process_type_name(process_id_stop))
            else:
                _process.kill()
                self.info("PyROS: didn't respond so killed " + self.get_process_type_name(process_id_stop))
                self.output(process_id_stop, "PyROS: didn't respond so killed " + self.get_process_type_name(process_id_stop))
    
            final_process_kill(process_id_stop)
    
        if process_id in self.processes:
            process = self.get_process_process(process_id)
            if process is not None:
                if process.returncode is None:
                    self.client.publish("exec/" + process_id + "/system", "stop")
                    thread = threading.Thread(target=wait_for_process_stop, args=(process_id,), daemon=True)
                    thread.start()
                else:
                    self.info("PyROS self.info: already finished " + self.get_process_type_name(process_id) + " return code " + str(process.returncode))
                    self.output(process_id, "PyROS self.info: already finished " + self.get_process_type_name(process_id) + " return code " + str(process.returncode))
                    final_process_kill(process_id)
            else:
                self.info("PyROS self.info: process " + process_id + " is not running.")
                self.output(process_id, "PyROS self.info: process " + process_id + " is not running.")
                final_process_kill(process_id)
        else:
            self.info("PyROS ERROR: process " + process_id + " does not exist.")
            self.output(process_id, "PyROS ERROR: process " + process_id + " does not exist.")
            final_process_kill(process_id)
            if restart:
                start_it_again(process_id)

    def restart_process(self, process_id: str) -> None:
        if process_id in self.processes:
            self.stop_process(process_id, restart=True)
            # self.start_process(processId)
            # if self.is_service(processId):
            #     self.output(processId, "PyROS: Restarted service " + processId)
            # else:
            #     self.output(processId, "PyROS: Restarted process " + processId)
        else:
            self.output(process_id, "PyROS ERROR: process " + process_id + " does not exist.")

    def remove_process(self, process_id: str) -> None:
        if process_id in self.processes:
            self.stop_process(process_id)
    
            if os.path.exists(self.process_dir(process_id)):
                p_dir = self.process_dir(process_id)
            else:
                self.output(process_id, "PyROS ERROR: cannot find process files")
                return
    
            files = os.listdir(p_dir)
            for file in files:
                os.remove(p_dir + "/" + file)
                if os.path.exists(p_dir + "/" + file):
                    self.output(process_id, "PyROS ERROR: cannot remove file " + p_dir + "/" + file)
    
            os.removedirs(p_dir)
            if os.path.exists(p_dir):
                self.output(process_id, "PyROS ERROR: cannot remove dir " + p_dir)
    
            del self.processes[process_id]
    
            self.output(process_id, "PyROS: removed " + self.get_process_type_name(process_id))
        else:
            self.output(process_id, "PyROS ERROR: process " + process_id + " does not exist.")

    def read_log(self, process_id: str) -> None:
        if process_id in self.processes:
            logs = self.processes[process_id]["logs"]
            if logs is None:
                logs = []
    
            for log in logs:
                self._output(process_id, log)

    def make_service_process(self, process_id: str) -> None:
        if process_id in self.processes:
            if self.processes[process_id]["type"] == "service":
                self.output(process_id, "PyROS: " + process_id + " is already service")
            else:
                self.processes[process_id]["type"] = "service"
                self.processes[process_id]["enabled"] = "True"

                properties = self.load_service_file(process_id)
                properties["type"] = "service"
                properties["enabled"] = "True"
                self.save_service_file(process_id, properties)
                self.output(process_id, "PyROS: made " + process_id + " service")
        else:
            self.output(process_id, "PyROS ERROR: process " + process_id + " does not exist.")

    def set_executable_process(self, process_id, args):
        if len(args) > 0:
            if process_id in self.processes:
                properties = self.load_service_file(process_id)
                self.processes[process_id]["exec"] = args[0]
                properties["exec"] = args[0]
                self.save_service_file(process_id, properties)
            else:
                self.output(process_id, "PyROS ERROR: process " + process_id + " does not exist.")
        else:
            self.output(process_id, "PyROS ERROR: set executable for " + process_id + " missing argument.")

    def unmake_service_process(self, process_id: str) -> None:
        if process_id in self.processes:
            if os.path.exists(self.process_service_filename(process_id)):
                if not os.remove(self.process_service_filename(process_id)):
                    self.output(process_id, "PyROS ERROR: failed to unmake process " + process_id + "; failed deleting .process file.")
    
            self.processes[process_id]["type"] = "process"
            del self.processes[process_id]["enabled"]
    
        else:
            self.output(process_id, "PyROS ERROR: process " + process_id + " does not exist.")

    def enable_service_process(self, process_id: str) -> None:
        if process_id in self.processes:
            if self.processes[process_id]["type"] != "service":
                self.make_service_process(process_id)
            else:
                properties = self.load_service_file(process_id)
                properties["enabled"] = "True"
                self.save_service_file(process_id, properties)
    
                self.processes[process_id]["enabled"] = "True"
    
            self.output(process_id, "PyROS: enabled " + process_id + " service")
        else:
            self.output(process_id, "PyROS ERROR: process " + process_id + " does not exist.")

    def disable_service_process(self, process_id: str) -> None:
        if process_id in self.processes:
            if self.processes[process_id]["type"] == "service":
                properties = self.load_service_file(process_id)
                properties["enabled"] = "False"
                self.save_service_file(process_id, properties)
    
                self.processes[process_id]["enabled"] = "False"
    
                self.output(process_id, "PyROS: enabled " + process_id + " service")
            else:
                self.output(process_id, "PyROS: " + process_id + " not a service")
    
        else:
            self.output(process_id, "PyROS ERROR: process " + process_id + " does not exist.")

    def make_agent_process(self, process_id: str) -> None:
        if process_id in self.processes:
            if self.processes[process_id]["type"] == "agent":
                self.output(process_id, "PyROS: " + process_id + " is already agent")
    
                self.processes[process_id]["lastPing"] = time.time()
            else:
                self.processes[process_id]["type"] = "agent"
                self.processes[process_id]["enabled"] = "True"
                self.processes[process_id]["lastPing"] = time.time()
    
                properties = self.load_service_file(process_id)
                properties["type"] = "agent"
                properties["enabled"] = "True"
                self.save_service_file(process_id, properties)
                self.output(process_id, "PyROS: made " + process_id + " an agent")
        else:
            self.output(process_id, "PyROS ERROR: process " + process_id + " does not exist.")

    def ping_process(self, process_id: str) -> None:
        if process_id in self.processes:
            self.processes[process_id]["lastPing"] = time.time()
        else:
            self.output(process_id, "PyROS ERROR: process " + process_id + " does not exist.")

    def ps_comamnd(self, command_id, _arguments):
        for process_id in self.processes:
            process = self.get_process_process(process_id)
            if process is not None:
                return_code = process.returncode
                if return_code is None:
                    status = "running"
                    return_code = "-"
                    if "old" in self.processes[process_id] and self.processes[process_id]["old"]:
                        status = "running-old"
                else:
                    status = "stopped"
                    return_code = str(return_code)
    
            else:
                status = "new"
                return_code = ""
    
            filename = self.process_filename(process_id)
    
            file_len = "-"
            file_date = "-"
    
            if filename is not None and os.path.exists(filename):
                file_stat = os.stat(filename)
                file_len = str(file_stat.st_size)
                file_date = str(file_stat.st_mtime)
    
            last_ping = "-"
            if "lastPing" in self.processes[process_id]:
                last_ping = str(self.processes[process_id]["lastPing"])
    
            self.system_output(command_id,
                               "{0} {1} {2} {3} {4} {5} {6}".format(
                                   self.complex_process_id(process_id),
                                   self.get_process_type_name(process_id),
                                   status,
                                   return_code,
                                   file_len,
                                   file_date,
                                   last_ping))
    
    def services_command(self, command_id, _arguments):
        for service_id in self.processes:
            if self.is_service(service_id):
                self.system_output(command_id, service_id)

    def stop_pyros_command(self, command_id, arguments):
    
        def stop_all_processes(_command_id, excludes):

            def are_all_stopped():
                for _pId in self.processes:
                    if _pId not in excludes and self.is_running(_pId):
                        return False
                return True
    
            for process_id in self.processes:
                if process_id not in excludes and self.is_running(process_id):
                    self.important("    Stopping process " + process_id)
                    self.stop_process(process_id)
    
            self.important("Stopping PyROS...")
            self.important("    excluding self.processes " + ", ".join(excludes))
            _now = time.time()
            while not are_all_stopped() and time.time() - _now < self.thread_kill_timeout * 2:
                time.sleep(0.02)
    
            not_stopped = []
            for _processId in self.processes:
                if _processId not in excludes and self.is_running(_processId):
                    not_stopped.append(_processId)
    
            if len(not_stopped) > 0:
                self.important("    Not all self.processes stopped; " + ", ".join(not_stopped))
    
            self.important("    sending feedback that we will stop (topic system/" + _command_id + ")")
    
            self.system_output(_command_id, "stopped")
    
            time.sleep(2)
            self.do_exit = True
    
        if command_id == "pyros.py:" + (self.this_cluster_id if self.this_cluster_id is not None else "master"):
            thread = threading.Thread(target=stop_all_processes, args=(command_id, arguments), daemon=True)
            thread.start()

    def process_command(self, process_id, message):
        self.trace("Processing received comamnd " + message)
        params = message.split(" ")
        command = params[0]
        if "stop" == command:
            self.stop_process(process_id)
        elif "start" == command:
            self.start_process(process_id)
        elif "restart" == command:
            self.restart_process(process_id)
        elif "remove" == command:
            self.remove_process(process_id)
        elif "logs" == command:
            self.read_log(process_id)
        elif "make-service" == command:
            self.make_service_process(process_id)
        elif "unmake-service" == command:
            self.unmake_service_process(process_id)
        elif "disable-service" == command:
            self.disable_service_process(process_id)
        elif "enable-service" == command:
            self.enable_service_process(process_id)
        elif "make-agent" == command:
            self.make_agent_process(process_id)
        elif "set-executable" == command:
            self.set_executable_process(process_id, params[1:])
        elif "ping" == command:
            self.ping_process(process_id)
        else:
            self.output(process_id, "PyROS ERROR: Unknown command " + command)

    def process_system_command(self, command_id, command_line):
        arguments = command_line.split(" ")
        command = arguments[0]
        del arguments[0]

        self.trace("Processing received system command " + command + ", args=" + str(arguments))
        if command == "ps":
            self.ps_comamnd(command_id, arguments)
        elif command == "services":
            self.services_command(command_id, arguments)
        elif command == "stop":
            self.stop_pyros_command(command_id, arguments)
        else:
            self.system_output(command_id, "Command " + command_line + " is not implemented")

        self.system_output_eof(command_id)

    def on_connect(self, mqtt_client, _data, _flags, rc):
        try:
            if rc == 0:
                mqtt_client.subscribe("system/+", 0)
                mqtt_client.subscribe("exec/+", 0)
                mqtt_client.subscribe("exec/+/process", 0)
                mqtt_client.subscribe("exec/+/process/#", 0)
                mqtt_client.subscribe("exec/+/system/stop", 0)
            else:
                self.important("ERROR: Connection returned error result: " + str(rc))
                # noinspection PyProtectedMember
                os._exit(rc)
        except Exception as exception:
            self.important("ERROR: Got exception on connect; " + str(exception))

    def on_message(self, _mqtt_client, _data, msg):
        def split_process_id(_process_id):
            _split = _process_id.split(":")
            if len(_split) == 1:
                return "master", _process_id
        
            return _split[0], _split[1]
        
        def check_cluster_id(_cluster_id):
            if self.this_cluster_id is None:
                return _cluster_id == 'master'
            else:
                return self.this_cluster_id == _cluster_id
        
        try:
            # payload = str(msg.payload, 'utf-8')
            topic = msg.topic
        
            if topic.startswith("exec/") and topic.endswith("/process"):
                process_id = topic[5:len(topic) - 8]
                cluster_id, process_id = split_process_id(process_id)
                if check_cluster_id(cluster_id):
                    payload = str(msg.payload, 'utf-8')
                    self.store_code(process_id, payload)
            elif topic.startswith("exec/"):
                split = topic[5:].split("/")
                if len(split) == 1:
                    process_id = topic[5:]
                    cluster_id, process_id = split_process_id(process_id)
                    if check_cluster_id(cluster_id):
                        if process_id in self.processes:
                            payload = str(msg.payload, 'utf-8')
                            self.process_command(process_id, payload)
                        else:
                            self.output(process_id, "No such process '" + process_id + "'")
                elif len(split) >= 3 and split[1] == "process":
                    process_id = split[0]
                    cluster_id, process_id = split_process_id(process_id)
                    if check_cluster_id(cluster_id):
                        name = "/".join(split[2:])
                        self.store_extra_code(process_id, name, msg.payload)
                elif len(split) == 3 and split[1] == "system" and split[2] == "stop":
                    process_id = split[0]
                    cluster_id, process_id = split_process_id(process_id)
                    if check_cluster_id(cluster_id):
                        payload = str(msg.payload, 'utf-8')
                        if payload == "stopped":
                            self.processes[process_id]['stop_response'] = True
        
            elif topic.startswith("system/"):
                command_id = topic[7:]
                payload = str(msg.payload, 'utf-8')
                self.process_system_command(command_id, payload)
            else:
                self.important("ERROR: No such topic " + topic)
        except Exception as exception:
            self.important("ERROR: Got exception on message; " + str(exception) + "\n" + ''.join(traceback.format_tb(exception.__traceback__)))

    def startup_services(self):
        if not os.path.exists(self.code_dir_name):
            os.mkdir(self.code_dir_name)
        programs_dirs = os.listdir(self.code_dir_name)
        for program_dir in programs_dirs:
            if os.path.isdir(self.process_dir(program_dir)):
                if os.path.exists(self.process_filename(program_dir)):
                    properties = self.load_service_file(program_dir)
                    if "type" not in properties:
                        properties["type"] = "process"
    
                    if "exec" not in properties:
                        properties["exec"] = "python3"
    
                    self.processes[program_dir] = {"type": properties["type"], "exec": properties["exec"]}
                    if self.is_service(program_dir):
                        if "enabled" in properties and properties["enabled"] == "True":
                            self.processes[program_dir]["enabled"] = "True"
                        else:
                            self.processes[program_dir]["enabled"] = "False"
    
                        if self.processes[program_dir]["enabled"] == "True":
                            self.start_process(program_dir)

    def test_for_agents(self, current_time):
        for process_id in self.processes:
            if self.is_agent(process_id) and self.is_running(process_id):
                if "lastPing" not in self.processes[process_id] or self.processes[process_id]["lastPing"] < current_time - self.agents_kill_timeout:
                    self.stop_process(process_id)

    def _connect_mqtt(self):
        _connect_retries = 0
        _connected_successfully = False
        while not _connected_successfully:
            _try_lasted = 0
            _now = time.time()
            try:
                self.important("    Connecting to " + str(self.host) + ":" + str(self.port) + " (self.timeout " + str(self.timeout) + ").")
                _now = time.time()
                self.client.connect(self.host, self.port, self.timeout)
                _connected_successfully = True
            except BaseException as _e:
                _try_lasted = time.time() - _now
                self.important("    Failed to connect, retrying; error " + str(_e))
                _connect_retries += 1
                if _try_lasted < 1:
                    time.sleep(1)
                if _connect_retries > self.max_reconnect_retries:
                    self.important("FATAL: leaving after too many retries.")
                    sys.exit(1)

    def start(self, name, args):
        self.process_configuration(name, args)

        self.important("Starting PyROS...")

        client_name = "PyROS"
        if self.this_cluster_id is not None:
            client_name += ":" + str(self.this_cluster_id)

        self.client = mqtt.Client(client_name)

        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message

        self._connect_mqtt()

        self.important("Started PyROS.")

        self.startup_services()

        last_checked_agents = time.time()

        while not self.do_exit:
            try:
                for it in range(0, 10):
                    time.sleep(0.009)
                    self.client.loop(0.001)
                now = time.time()
                if now - last_checked_agents > self.agents_check_timeout:
                    last_checked_agents = now
                    self.test_for_agents(now)

            except SystemExit:
                self.do_exit = True
            except Exception as e:
                self.important("ERROR: Got exception in discovery loop; " + str(e))

        self.important("PyROS stopped.")


if __name__ == "__main__":
    PyrosDaemon().start(sys.argv[0], sys.argv[1:])
