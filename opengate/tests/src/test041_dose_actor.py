#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate

paths = gate.get_default_test_paths(__file__, "gate_test008_dose_actor")

# create the simulation
sim = gate.Simulation()

# main options
ui = sim.user_info
ui.g4_verbose = False
ui.g4_verbose_level = 1
ui.visu = False
ui.random_seed = 123456

# units
m = gate.g4_units("m")
cm = gate.g4_units("cm")
mm = gate.g4_units("mm")
MeV = gate.g4_units("MeV")
Bq = gate.g4_units("Bq")

#  change world size
world = sim.world
world.size = [0.5 * m, 0.5 * m, 0.5 * m]

# waterbox
waterbox = sim.add_volume("Box", "waterbox")
waterbox.size = [10 * cm, 10 * cm, 10 * cm]
waterbox.material = "G4_WATER"
waterbox.color = [0, 0, 1, 1]

# lungbox
lungbox = sim.add_volume("Box", "lungbox")
lungbox.mother = waterbox.name
lungbox.size = [10 * cm, 10 * cm, 4 * cm]
lungbox.translation = [0 * cm, 0 * cm, 2.5 * cm]
lungbox.material = "G4_LUNG_ICRP"
lungbox.color = [0, 1, 1, 1]

# bonebox
bonebox = sim.add_volume("Box", "bonebox")
bonebox.mother = waterbox.name
bonebox.size = [10 * cm, 10 * cm, 4 * cm]
bonebox.translation = [0 * cm, 0 * cm, -2.5 * cm]
bonebox.material = "G4_BONE_CORTICAL_ICRP"
bonebox.color = [1, 0, 0, 1]

# physics
p = sim.get_physics_user_info()
p.physics_list_name = "QGSP_BERT_EMV"
sim.set_cut("world", "all", 1 * mm)

# default source for tests
source = sim.add_source("Generic", "mysource")
source.energy.mono = 115 * MeV
source.particle = "proton"
source.position.type = "disc"
source.position.radius = 1 * cm
source.position.translation = [0, 0, -80 * mm]
source.direction.type = "momentum"
source.direction.momentum = [0, 0, 1]
source.activity = 5000 * Bq

# add dose actor
dose = sim.add_actor("DoseActor", "dose")
dose.output = paths.output / "test041-edep.mhd"
dose.mother = "waterbox"
dose.size = [10, 10, 50]
mm = gate.g4_units("mm")
ts = [200 * mm, 200 * mm, 200 * mm]
dose.spacing = [x / y for x, y in zip(ts, dose.size)]
print(dose.spacing)
dose.uncertainty = True
dose.gray = True
dose.hit_type = "random"

# add stat actor
s = sim.add_actor("SimulationStatisticsActor", "Stats")
s.track_types_flag = True

# start simulation
output = sim.start(True)

# print results at the end
stat = output.get_actor("Stats")
print(stat)

dose = output.get_actor("dose")
print(dose)

# tests
gate.warning("Tests stats file")
stats_ref = gate.read_stat_file(paths.gate_output / "stat2.txt")
is_ok = gate.assert_stats(stat, stats_ref, 0.10)

gate.warning("\nDifference for EDEP")
is_ok = (
    gate.assert_images(
        paths.gate_output / "output2-Edep.mhd",
        paths.output / "test041-edep.mhd",
        stat,
        tolerance=10,
        ignore_value=0,
    )
    and is_ok
)

gate.warning("\nDifference for uncertainty")
is_ok = (
    gate.assert_images(
        paths.gate_output / "output2-Edep-Uncertainty.mhd",
        paths.output / "test041-edep_uncertainty.mhd",
        stat,
        tolerance=30,
        ignore_value=1,
    )
    and is_ok
)

gate.warning("\nDifference for dose in Gray")
is_ok = (
    gate.assert_images(
        paths.gate_output / "output2-Dose.mhd",
        paths.output / "test041-edep_dose.mhd",
        stat,
        tolerance=10,
        ignore_value=0,
    )
    and is_ok
)

gate.test_ok(is_ok)
