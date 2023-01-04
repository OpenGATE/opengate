#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
from box import Box
from opengate.contrib.dose_rate_helpers import dose_rate

paths = gate.get_default_test_paths(__file__, "")
dr_data = paths.data / "dose_rate_data"

# set param
gcm3 = gate.g4_units("g/cm3")
param = Box()
param.ct_image = str(dr_data / "29_CT_5mm_crop.mhd")
param.table_mat = str(dr_data / "Schneider2000MaterialsTable.txt")
param.table_density = str(dr_data / "Schneider2000DensitiesTable.txt")
param.activity_image = str(dr_data / "activity_test_crop_4mm.mhd")
param.radionuclide = "Lu177"
param.activity_bq = 1e6
param.number_of_threads = 1
param.visu = False
param.verbose = True
param.density_tolerance_gcm3 = 0.05
param.output_folder = str(paths.output / "output_test035")

# Create the simu
# Note that the returned sim object can be modified to change source or cuts or whatever other parameters
sim = dose_rate(param)

# Change source to alpha to get quick high local dose
source = sim.get_source_user_info("vox")
source.particle = "alpha"
MeV = gate.g4_units("MeV")
source.energy.mono = 1 * MeV

print("Phys list cuts:")
print(sim.physics_manager.dump_cuts())

# run
output = sim.start(True)

# print results
print()
gate.warning(f"Check stats")
stats = output.get_actor("Stats")
stats.write(param.output_folder / "stats035.txt")
print(stats)
stats_ref = gate.read_stat_file(paths.output_ref / "output_test035" / "stats.txt")
is_ok = gate.assert_stats(stats, stats_ref, 0.10)

# dose comparison
print()
gate.warning(f"Check dose")
h = output.get_actor("dose")
print(h)
is_ok = (
    gate.assert_images(
        paths.output_ref / "output_test035" / "edep.mhd",
        h.user_info.output,
        stats,
        tolerance=15,
        ignore_value=0,
    )
    and is_ok
)

gate.test_ok(is_ok)
