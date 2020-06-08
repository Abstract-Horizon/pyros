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


import time

LOG_LEVEL_OFF = 0  # To be used when setting up level
LOG_LEVEL_ALWAYS = 1  # To be used when logging or setting up level
LOG_LEVEL_ERROR = 1  # To be used when logging or setting up level
LOG_LEVEL_INFO = 2  # To be used when logging or setting up level
LOG_LEVEL_DEBUG = 3  # To be used when logging or setting up level
LOG_LEVEL_TRACE = 4  # To be used when logging or setting up level
LOG_LEVEL_ALL = 10  # To be used when setting up level

LOG_LEVEL = LOG_LEVEL_ALL


def formatArgL(label, value, fieldSize):
    if len(label) > 0:
        return label + ":" + str(value).ljust(fieldSize)
    else:
        return str(value).ljust(fieldSize)


def formatArgR(label, value, fieldSize):
    if len(label) > 0:
        return label + ":" + str(value).rjust(fieldSize)
    else:
        return str(value).rjust(fieldSize)


def log(level, what):
    if level <= LOG_LEVEL:
        print(what)


def info(what):
    if LOG_LEVEL_INFO <= LOG_LEVEL:
        print(what)


def debug(what):
    if LOG_LEVEL_DEBUG <= LOG_LEVEL:
        print(what)


def logArgs(*msg):
    tnow = time.time()

    logMsg = formatArgR("", int(tnow * 1000) % 100000, 7) + " " + " ".join(msg)
    log(LOG_LEVEL_DEBUG, logMsg)
