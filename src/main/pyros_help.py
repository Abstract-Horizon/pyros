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

try:
    with Resource("VERSION") as f:
        version = f.readline().decode('ascii').replace('\n', '')

    print("pyros version " + version)
    print("")
except FileNotFoundError as ignore:
    pass

print("usage: pyros [<host[:port]>] <command> [<args>]")
print("")
print("There are commond PyROS commands used in various situations:")
print("")
print("local commands")
print("   alias      sets, removes or displays hostname/address aliases used for PyROS commands")
print("")
print("system wide commands")
print("   ps         lists all processes")
# print("   service    lists services only")
print("")
print("process specific commands")
print("   upload     uploads code")
print("   service    enables/disables, makes/unmakes a process to a service")
print("   start      starts service or process")
print("   stop|kill  stops service or process")
print("   restart    restarts service or process")
print("   remove|rm  removes service or process")
print("   shutdown   shuts down rover's Raspberry Pi")
print("   log        obtains logs of a service or process")
print("   stats      starts/stops collecting and obtains stats for a process")
print("   discover   shows rover present on the local network")
print("   storage    sets/reads from rover's storage (registry)")
print("   wifi       shows or sets rover's wifi settings")
print("")
print("If <host> is suppolied then comamnd will apply to that server. Otherwise")
print("it will use 'default' alias if set. <host> can be only hostname, ip address or")
print("combination of host and port in 'host:port'.")
print("")
print("For more information for each command do pyros.py <command> -h")
