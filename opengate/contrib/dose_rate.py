#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
import click
import json
from box import Box
from opengate.contrib.dose_rate_helpers import dose_rate

CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])


@click.command(context_settings=CONTEXT_SETTINGS)
@click.argument("json_param", nargs=1)
@click.option("--output_folder", "-o", default="AUTO", help="output folder, auto=rnd")
def go(json_param, output_folder):
    # open the param file
    try:
        f = open(json_param, "r")
        param = json.load(f)
    except IOError:
        print(f"Cannot open input json file {json_param}")
    param = Box(param)
    print(param)

    # set or create output_folder
    if output_folder == "AUTO":
        output_folder = gate.get_random_folder_name()
    param.output_folder = output_folder

    # set activity as int (to deal with 1e4 notation)
    param.activity_bq = int(float(param.activity_bq))

    # create the simu
    sim = dose_rate(param)

    # run
    sim.initialize()
    sim.start()

    # print results at the end
    stats = sim.get_actor("Stats")
    print(stats)
    stats.write(param.output_folder / "stats.txt")
    print(f"Output in {param.output_folder}")


# --------------------------------------------------------------------------
if __name__ == "__main__":
    go()
