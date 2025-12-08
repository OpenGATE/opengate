#!/usr/bin/env python3
# -*- coding: utf-8 -*-

### Derenzo phantom with 6 sets of cylinders of different size for each set
### For phantom1 set of cylinders each cylinder is assigned with an activity value
### The same procedure as in phantom1 with the activity can be followed to all phantom sets

import opengate as gate
import opengate.contrib.phantoms.derenzo as derenzo
import itk
from opengate.tests import utility

# Define the units used in the simulation set-up
mm = gate.g4_units.mm
cm = gate.g4_units.cm
Bq = gate.g4_units.Bq
cm3 = gate.g4_units.cm3
MeV = gate.g4_units.MeV
BqmL = Bq / cm3

if __name__ == "__main__":
    # create the simulation
    sim = gate.Simulation()

    paths = utility.get_default_test_paths(__file__, "", "test093")

    # Add a material database
    sim.volume_manager.add_material_database(paths.data / "GateMaterials.db")

    # Change world size
    world = sim.world
    world.size = [100 * cm, 100 * cm, 100 * cm]

    # Add the derenzo phantom
    derenzo_phantom = derenzo.add_derenzo_phantom(sim)
    a = 20 * BqmL
    activity_Bq_mL = [10 * a, 2 * a, 3 * a, 4 * a, 5 * a, 6 * a]
    sources = derenzo.add_sources(sim, derenzo_phantom, activity_Bq_mL)
    for source in sources:
        source.particle = "alpha"
        source.energy.type = "mono"
        source.energy.mono = 100 * MeV
        source.direction.type = "momentum"
        source.direction.momentum = [0, 1, 0]

    # Add a plan above the phantom
    plan = sim.add_volume("Box", "plan")
    plan.mother = world.name
    plan.size = [35 * cm, 1 * cm, 35 * cm]
    plan.material = "Tungsten"
    plan.translation = derenzo_phantom.translation
    plan.translation[1] += 10 * cm

    # Physics
    sim.physics_manager.physics_list_name = "G4EmStandardPhysics_option3"
    sim.physics_manager.enable_decay = True

    # Acquisition options
    sim.check_volumes_overlap = True
    sim.g4_verbose = False
    sim.g4_verbose_level = 1
    sim.visu = False
    sim.visu_type = "qt"
    # sim.visu_verbose = True
    # sim.progress_bar = True
    sim.number_of_threads = 1
    sim.output_dir = paths.output
    sim.random_seed = 23654987

    # Actor
    stats_actor = sim.add_actor("SimulationStatisticsActor", "stats")
    stats_actor.track_types_flag = True
    stats_actor.output_filename = "test093_derenzo_stats.txt"

    dose_actor = sim.add_actor("DoseActor", "dose")
    dose_actor.edep.output_filename = "test093_derenzo_edep.mhd"
    dose_actor.attached_to = plan.name
    dose_actor.size = [350, 1, 350]
    dose_actor.spacing = [1 * mm, 10 * mm, 1 * mm]

    # run
    sim.run()

    # compare stats
    stats_ref = utility.read_stats_file(paths.output_ref / "test093_derenzo_stats.txt")
    is_ok = utility.assert_stats(stats_actor, stats_ref, tolerance=0.05)
    is_ok = is_ok and utility.assert_img_sum(
        itk.imread(paths.output_ref / "test093_derenzo_edep.mhd"),
        itk.imread(paths.output / "test093_derenzo_edep.mhd"),
        sum_tolerance=5,
    )
    utility.test_ok(is_ok)
