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
import zipfile
import sys
import os


zip_file = None
_zip_file = None

_this_path = None

if zipfile.is_zipfile(sys.argv[0]):
    _zip_file = sys.argv[0]
    zip_file = zipfile.ZipFile(_zip_file)
else:
    _this_path = os.path.abspath(os.path.dirname(sys.argv[0]))


def get_this_path_or_file():
    if _zip_file is not None:
        return _zip_file
    else:
        return _this_path


class Resource:
    def __init__(self, path):
        path = path[:-1] if path.startswith("/") else path

        self.path = path
        if zip_file is None:
            if 'PYTHONPATH' not in os.environ:
                raise FileNotFoundError(path)

            if path != "":
                files = [file for file in [os.path.join(d, path) for d in (os.environ['PYTHONPATH'].split(':'))] if os.path.exists(file)]

                if len(files) > 0:
                    self.path = files[0]
                else:
                    raise FileNotFoundError(path)

    def list(self):
        if zip_file is None:
            pythonpaths = [d for d in (os.environ['PYTHONPATH'].split(':')) if os.path.exists(d)]

            if "" == self.path:
                return [f + "/" if os.path.isdir(os.path.join(path, f)) else f for path in pythonpaths for f in os.listdir(path)]
            else:
                paths = [os.path.join(path, self.path) for path in pythonpaths if os.path.exists(os.path.join(path, self.path))]
                return [f + "/" if os.path.isdir(os.path.join(path, f)) else f for path in paths for f in os.listdir(path)]
        else:
            path = self.path
            if len(path) > 1 and not path.endswith("/"):
                path = path + "/"
            file_list = zip_file.namelist()
            return [n[len(path):] for n in file_list if n.startswith(path) and "/" not in n[len(path):]] + \
                   [n for n in set([n[:n.find("/") + 1] for n in [n[len(path):] for n in file_list if n.startswith(path) and "/" in n[len(path):]]])]

    def __enter__(self):
        if zip_file is None:
            self.resource = open(self.path, 'rb')
        else:
            try:
                self.resource = zip_file.open(self.path)
            except KeyError:
                raise FileNotFoundError(self.path)

        self.resource.__enter__()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.resource.__exit__(exc_type, exc_val, exc_tb)

    def read(self):
        return self.resource.read()

    def readline(self):
        return self.resource.readline()

    def readlines(self):
        return self.resource.readlines()

    def seek(self):
        return self.resource.seek()

    def tell(self):
        return self.resource.tell()

    def __iter__(self):
        return self.resource.__iter__()

    def __next__(self):
        return self.resource.__next()
