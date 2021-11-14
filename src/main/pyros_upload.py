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
import time

from pyros_common import CommonCommand


class PyrosUpload(CommonCommand):
    def __init__(self):
        super(PyrosUpload, self).__init__(__name__)
        self.parser.add_argument("-s", "--service", action="store_true", default=False, help="uploaded code is to be set as service.")
        self.parser.add_argument("-r", "--restart", action="store_true", default=False, help="restarts uploaded service.")
        self.parser.add_argument("-x", "--exec", help="sets executable to be used to start program. If omitted 'python3' is used by default.")
        self.parser.add_argument("-f", "--tail", action="store_true", default=False, help="'tail' messages out of process.")
        self.parser.add_argument("process_id", help="id process is going to be known from this point on.")
        self.parser.add_argument("file", nargs='?', help="main file name to be uploaded.")
        group = self.parser.add_argument_group()
        group.add_argument("-e", "--extra", nargs=argparse.ZERO_OR_MORE, help="extra files to be uploaded along with the main file.")

        self.process_id = None
        self.service = False
        self.restart = False
        self.tail = False
        self.executable = None

        self.filename = None

        self.extra_files = []

        self.had_start = False
        self.pyros_client = None
        self.files = []

    def execute_command(self, client):
        def send_file(dest_path, filename):
            if self.verbose_level >= 1:
                print(f"Sending file '{filename}' to '{dest_path}'")
            with open(filename, "rb") as f:
                content = f.read()

                extra_name = os.path.join(dest_path, os.path.split(filename)[1])
                self.files.append(extra_name)

                if self.verbose_level >= 2:
                    print(f"Sending file content to exec/{self.process_id}/process/{extra_name}, content len {len(content)}")
                client.publish(f"exec/{self.process_id}/process/{extra_name}", content)
                time.sleep(0.1)

        def process_dir(dest_path, dir_path):
            for f in os.listdir(dir_path):
                if not f.endswith('__pycache__'):
                    if os.path.isdir(f):
                        process_dir(os.path.join(dest_path, f), os.path.join(dir_path, f))
                    else:
                        send_file(dest_path, os.path.join(dir_path, f))

        self.pyros_client = client

        if self.filename is not None:
            with open(self.filename) as file:
                file_content = file.read()

            if self.verbose_level >= 2:
                print(f"Sending file content to exec/{self.process_id}/process")
            client.publish(f"exec/{self.process_id}/process", file_content)
            time.sleep(0.1)

            if self.service:
                if self.verbose_level >= 2:
                    print(f"Sending exec/{self.process_id}, make-service")
                    print(f"Sending exec/{self.process_id}, make-service")
                client.publish(f"exec/{self.process_id}", "enable-service")
                time.sleep(0.1)
                client.publish(f"exec/{self.process_id}", "enable-service")
                time.sleep(0.1)

            if self.executable is not None:
                if self.verbose_level >= 2:
                    print(f"Sending exec/{self.process_id}, set-executable")
                client.publish(f"exec/{self.process_id}", f"set-executable {self.executable}")
                time.sleep(0.1)

        if self.extra_files is not None:
            for extra_file in self.extra_files:
                if os.path.isdir(extra_file):
                    process_dir(os.path.split(extra_file)[1], extra_file)
                else:
                    send_file("", extra_file)

        return False

    def process_out(self, line, _pid):
        if line.endswith("\n"):
            line = line[:len(line) - 1]
        if not self.tail:
            return False
        print(line)
        return True

    def process_status(self, line, pid):
        if line.startswith("stored "):
            file = line[7:]
            if file in self.files:
                i = self.files.index(file)
                del self.files[i]
                if len(self.files) == 0:
                    if self.restart:
                        if self.verbose_level >= 2:
                            print(f"Sending exec/{self.process_id}, set-restart")
                        self.pyros_client.publish("exec/{self.process_id}", "restart")
                    else:
                        return False
        elif self.restart and line.startswith("PyROS: started"):
            self.had_start = True
            if self.tail:
                print("Process " + pid + " is restarted. Showing output:")
            else:
                print("Process " + pid + " is restarted.")
            return self.tail
        return True

    def run(self):
        args = self.process_common_args_for_remote_command()
        self.service = args.service
        self.restart = args.restart
        self.tail = args.tail
        self.process_id = args.process_id
        self.executable = args.exec

        self.process_id = args.process_id
        self.filename = args.file

        self.extra_files = args.extra

        self.files = [self.process_id + ".py"]

        self.process_command(self.process_id, self.execute_command, self.process_out, self.process_status)


PyrosUpload().run()
