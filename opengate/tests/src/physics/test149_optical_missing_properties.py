#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Optical physics with a voxelized volume containing a material without optical
properties in the xml file (#452): the simulation must run, with a warning
(it previously failed with an AttributeError).
"""

import opengate as gate
from opengate.tests import utility
from opengate.utility import g4_units

if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, "test098", output_folder="test149")

    cm = g4_units.cm
    eV = g4_units.eV

    sim = gate.Simulation()
    sim.output_dir = paths.output
    sim.verbose_level = gate.logger.NONE
    sim.random_seed = 123456
    sim.volume_manager.add_material_database(paths.data / "GateMaterials.db")
    sim.physics_manager.special_physics_constructors.G4OpticalPhysics = True
    sim.physics_manager.optical_properties_file = (
        paths.data / "test098" / "Materials.xml"
    )

    sim.world.size = [6 * cm, 6 * cm, 2 * cm]
    sim.world.material = "Air"

    # "Lung" is not in the optical properties file
    vox = sim.add_volume("ImageVolume", "image")
    vox.image = paths.data / "test098" / "vox_volume.mhd"
    vox.material = "Air"
    vox.voxel_materials = [[-0.5, 0.5, "Adipose"], [0.5, 1.5, "Lung"]]

    source = sim.add_source("GenericSource", "source")
    source.particle = "opticalphoton"
    source.energy.mono = 1.913 * eV
    source.direction.type = "momentum"
    source.direction.momentum = [0, 0, 1]
    source.number_of_primaries = 100

    stats = sim.add_actor("SimulationStatisticsActor", "stats")
    sim.run()

    w = [x for x in sim.warnings if "optical material properties" in x and "Lung" in x]
    is_ok = len(w) > 0 and stats.counts.events == 100
    utility.print_test(is_ok, f"Run done, warning for 'Lung': {len(w) > 0}")
    utility.test_ok(is_ok)
