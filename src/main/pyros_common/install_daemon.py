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
import re

from pyros_common.utils import ensure_dir
from local_resources import Resource


class InstallDaemon:
    def __init__(self, home_dir, user, group, force=False):
        self.home_dir = home_dir
        self.user = user
        self.group = group
        self.force = force

    def _copy_recursively(self, resource, resource_path, dest_path, excludes=None, overwrite_dir_contents=False):

        def in_exclude(path, _excludes):
            for pattern in _excludes:
                if pattern.match(path):
                    return True
            return False

        exclude_patterns = [re.compile(e.replace("**", "(.*)").replace("*", "([^/]*)")) for e in (excludes if excludes is not None else [])]
        for file in resource.list():
            if file.endswith("/"):
                new_resource_path = os.path.join(resource_path, file[:-1])
                if excludes is None or not in_exclude(new_resource_path,  exclude_patterns):
                    if not ensure_dir(dest_path, self.user, self.group, file[:-1], verbose=False) or overwrite_dir_contents:
                        self._copy_recursively(Resource(new_resource_path), os.path.join(resource_path, file), os.path.join(dest_path, file[:-1]), excludes=excludes, overwrite_dir_contents=overwrite_dir_contents)
            else:
                new_resource_path = os.path.join(resource_path, file)
                if excludes is None or not in_exclude(new_resource_path,  exclude_patterns):
                    with Resource(new_resource_path) as r:
                        result_file = os.path.join(dest_path, file)
                        with open(result_file, 'wb') as out_file:
                            out_file.write(r.read())
                    os.system("chown " + self.user + ":" + self.group + " " + result_file)

    def _copy_existing_python_packages(self, code_dir, package_names):
        for package_name in package_names:
            print(f"Installing default package {package_name}")
            ensure_dir(code_dir, self.user, self.group, package_name, verbose=False)
            self._copy_recursively(Resource(package_name), package_name, os.path.join(code_dir, package_name), excludes=["**/__pycache__"])

    def install(self):
        if not os.path.exists(self.home_dir):
            print(f"ERROR: '{self.home_dir} does not exist.")
        else:
            print(f"Installing daemon with working directory as '{self.home_dir}'.")
            print(f"Will use user '{self.user}' to run daemon.")

            ensure_dir(self.home_dir, self.user, self.group, "logs", verbose=True)
            ensure_dir(self.home_dir, self.user, self.group, "data", verbose=True)
            if not ensure_dir(self.home_dir, self.user, self.group, "code", verbose=True) or self.force:
                code_dir = os.path.join(self.home_dir, "code")
                self._copy_existing_python_packages(code_dir, ["paho", "local_resources", "discovery", "pyroslib", "storage"])
                self._copy_recursively(Resource("pyros-code"), "pyros-code", code_dir, overwrite_dir_contents=True, excludes=["**/__pycache__"])

            config_file = os.path.join(self.home_dir, "pyros.config")
            if not os.path.exists(config_file):
                print(f"Creating default config file in {config_file}")
                with Resource("linux-service/pyros.config") as in_file:
                    with open(config_file, 'wb') as out_file:
                        out_file.write(in_file.read())

            if not os.path.exists("/etc/systemd/system/"):
                print("")
                print("ERROR: It seems that this system doesn't have systemd - directory '/etc/systemd/system/' is missing.")
                print("ERROR: No daemon will be installed.")
                print()
                print("To run pyros daemon try:")
                print(f"pyros daemon -d {self.home_dir}")
            else:
                if os.path.exists("/etc/systemd/system/pyros.service") and not self.force:
                    print("ERROR: '/etc/systemd/system/pyros.service' already exists. Use --force switch if you want to override it.")
                else:
                    print("Installing /etc/systemd/system/pyros.service")
                    with Resource("linux-service/pyros.service") as in_file:
                        try:
                            with open("/etc/systemd/system/pyros.service", 'wb') as out_file:
                                out_file.write(in_file.read()
                                               .replace(b"{HOME}", self.home_dir.encode('utf-8'))
                                               .replace(b"{USER}", self.user.encode('utf-8')))

                            print("Running: systemctl enable pyros.service")
                            os.system("systemctl enable pyros.service")

                            print("Daemon successfully installed. Do following to run it:")
                            print("sudo service pyros start")
                            print()
                            print("Don't forget to make sure you have MQTT installed or pyros.config to point to one.")
                        except PermissionError:
                            print("ERROR: Cannot install '/etc/systemd/system/pyros.service'.")
                            print("Maybe run this command with 'sudo'.")
