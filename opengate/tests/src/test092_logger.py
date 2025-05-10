#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from opengate.tests.utility import get_default_test_paths, test_ok, print_test
from opengate.utility import g4_units
from opengate.logger import INFO, DEBUG, RUN, NONE
from opengate.managers import Simulation


def rm_timing(s):
    return "\n".join(line for line in s.splitlines() if "Simulation: STOP." not in line)


if __name__ == "__main__":
    paths = get_default_test_paths(__file__, None, "test092")

    sim = Simulation()
    m = g4_units.m
    world = sim.world
    world.size = [3 * m, 3 * m, 3 * m]
    world.material = "G4_AIR"
    is_ok = True

    # no source, so a warning will be generated

    # add one actor for logger debug
    stats = sim.add_actor("SimulationStatisticsActor", "Stats")
    stats.track_types_flag = True

    # default verbose = INFO
    sim.verbose_level = INFO
    print(f"Logger: {sim.verbose_level}")
    sim.log_sink = "str"
    sim.run(start_new_process=True)
    print(sim.log_output)

    # test
    ref1 = paths.output_ref / "test092_log_output1.txt"
    # create the reference
    # with open(ref1, "w") as f:
    #    f.write(sim.log_output)
    with open(ref1, "r") as f:
        ref = f.read()
    # remove the line with the time
    ref = rm_timing(ref)
    sim.log_output = rm_timing(sim.log_output)
    b = ref == sim.log_output and is_ok
    print_test(b, "Compare output with logger level INFO")

    # test with no log
    print()
    print("-" * 79)
    sim.verbose_level = NONE
    sim.log_sink = "str"
    print(f"Logger: {sim.verbose_level}")
    sim.run(start_new_process=True)
    print("->", sim.log_output, "<-")

    # test
    b = "" == sim.log_output and is_ok
    print_test(b, "Compare output with logger level INFO")

    # test with debug
    print()
    print("-" * 79)
    sim.verbose_level = DEBUG
    sim.log_sink = "str"
    print(f"Logger: {sim.verbose_level}")
    sim.run()  # start_new_process=True)
    print(sim.log_output)

    # test
    ref2 = paths.output_ref / "test092_log_output2.txt"
    # create the reference
    # with open(ref2, "w") as f:
    #    f.write(sim.log_output)
    with open(ref2, "r") as f:
        ref = f.read()
    ref = rm_timing(ref)
    sim.log_output = rm_timing(sim.log_output)
    b = ref == sim.log_output and is_ok
    print_test(b, "Compare output with logger level DEBUG")

    test_ok(is_ok)
