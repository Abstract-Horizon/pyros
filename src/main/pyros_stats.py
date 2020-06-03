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


from pyros_common import CommonCommand


class PyrosStats(CommonCommand):
    def __init__(self):
        super(PyrosStats, self).__init__(__name__)
        self.parser.add_argument("command", choices=["start", "stop", "read"],
                                 help="'start': starts collecing PyROS stats for given process.\n"
                                      "'stop': stops collecting PyROS stats for given process.\n"
                                      "'read': reads stats for given process.")
        self.parser.add_argument("process_id", help="process id. ")
        self.process_id = None
        self.command = None
        self.got_stats = False

    def execute_command(self, client):
        client.subscribe("exec/" + self.process_id + "/stats/out", 0)
        client.publish("exec/" + self.process_id + "/stats", self.command)

        return self.command == "read"

    def process_out(self, msg, pid):

        if not pid.endswith("/stats"):
            return not self.got_stats

        tick = 0
        start_time = 0
        last_time = 0
        total_sent = 0
        total_rec = 0
        max_sent = 0
        max_rec = 0
        first = True
        second = False
        lines = msg.split("\n")
        for line in lines:
            line = line.strip()
            if len(line) > 0:
                data = line.split(",")
                t = float(data[0])
                sent = int(data[1])
                rec = int(data[2])
                if first:
                    start_time = t
                    first = False
                    second = True
                elif second:
                    second = False
                    tick = t - start_time
                last_time = t
                total_sent = total_sent + sent
                total_rec = total_rec + rec
                if sent > max_sent:
                    max_sent = sent
                if rec > max_rec:
                    max_rec = rec

        if tick > 0:
            tick_str = "{0:13.2f}".format(tick * 1000) + "ms"
        else:
            tick_str = "no data"

        total_time = last_time - start_time + tick
        total_time_str = "{0:8.4f}".format(total_time) + "s"

        print("{0:<16} {1:<16} {2:<16} {3:<16} {4:<16} {5:<16}".format(
            "tick", "total time", "received", "sent", "max received", "max sent"))
        print("{0:>16} {1:>16} {2:<16} {3:<16} {4:<16} {5:<16}".format(
            tick_str, total_time_str, str(total_rec), str(total_sent), str(max_rec), str(max_sent)))

        self.got_stats = True
        return False

    def process_status(self, _line, _pid):
        return True

    def run(self):
        args = self.process_common_args_for_remote_command()
        self.process_id = args.process_id
        self.command = args.command

        self.process_command(self.process_id, self.execute_command, self.process_out, self.process_status)


PyrosStats().run()
