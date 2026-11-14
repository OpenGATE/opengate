#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
A RepeatParametrisedVolume that is created but never added to the simulation
must not change the geometry: the repeated volume is still built and the
digitizer attached to it records hits (#857). When the repeater is added, the
repeated volume is replaced by the repetitions.
"""

import uproot
import opengate as gate
from opengate.geometry.volumes import RepeatParametrisedVolume
from opengate.tests import utility


def run(name, add_repeater):
    m = gate.g4_units.m
    cm = gate.g4_units.cm
    keV = gate.g4_units.keV

    sim = gate.Simulation()
    sim.output_dir = paths.output
    sim.verbose_level = gate.logger.NONE
    sim.random_seed = 123456
    sim.world.size = [1 * m, 1 * m, 1 * m]
    sim.world.material = "G4_AIR"

    detector = sim.add_volume("Box", "detector")
    detector.material = "G4_WATER"
    detector.size = [10 * cm, 10 * cm, 10 * cm]

    rpt = RepeatParametrisedVolume(name="repeat_detector", repeated_volume=detector)
    rpt.linear_repeat = [2, 1, 1]
    rpt.translation = [20 * cm, 0, 0]
    if add_repeater:
        sim.volume_manager.add_volume(rpt)

    source = sim.add_source("GenericSource", "source")
    source.particle = "gamma"
    source.energy.mono = 511 * keV
    source.direction.type = "iso"
    source.number_of_primaries = 2000

    hits = sim.add_actor("DigitizerHitsCollectionActor", "Hits")
    hits.attached_to = "detector"
    hits.output_filename = f"test144_{name}.root"
    hits.attributes = ["TotalEnergyDeposit", "PostPosition"]

    sim.run(start_new_process=True)
    return detector, hits.get_output_path()


if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, "", output_folder="test144")
    is_ok = True

    # 1) repeater created but not added: the detector is built as usual
    detector, path = run("not_added", add_repeater=False)
    b = detector.build_physical_volume is True
    utility.print_test(b, f"Repeater not added: detector still built ({b})")
    is_ok = is_ok and b
    b = path.exists()
    utility.print_test(b, f"Repeater not added: root file exists {path}")
    is_ok = is_ok and b
    if b:
        n = len(uproot.open(path)["Hits"]["TotalEnergyDeposit"].array())
        b = n > 0
        utility.print_test(b, f"Repeater not added: {n} hits in the detector")
        is_ok = is_ok and b

    # 2) repeater added: the detector (10 cm wide, at the centre) is replaced by
    # two copies centred at x = -10 cm and x = +10 cm: all hits at |x| > 5 cm
    detector, path = run("added", add_repeater=True)
    b = path.exists()
    utility.print_test(b, f"Repeater added: root file exists {path}")
    is_ok = is_ok and b
    if b:
        mm = gate.g4_units.mm
        x = uproot.open(path)["Hits"]["PostPosition_X"].array(library="np")
        b = len(x) > 0 and (x < 0).any() and (x > 0).any()
        b = b and (abs(x) > 50 * mm - 1e-6).all()
        utility.print_test(
            b,
            f"Repeater added: {len(x)} hits, only in the two copies "
            f"(min |x| = {abs(x).min():.1f} mm)",
        )
        is_ok = is_ok and b

    utility.test_ok(is_ok)
