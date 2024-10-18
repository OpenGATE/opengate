# Version Information
# Python:   3.9.18
# Pandas:   2.2.2
# NumPy:    1.24.1

import opengate as gate
import opengate.tests.utility as tu
from opengate.contrib.optical.optigan import Optigan

import os

if __name__ == "__main__":
    paths = tu.get_default_test_paths(__file__, output_folder="test075_optigan")

    # create simulation
    sim = gate.Simulation()
    sim.g4_verbose = True
    sim.output_dir = paths.output
    # sim.random_seed = 600

    # units
    m = gate.g4_units.m
    cm = gate.g4_units.cm
    mm = gate.g4_units.mm
    eV = gate.g4_units.eV
    MeV = gate.g4_units.MeV
    Bq = gate.g4_units.Bq

    # add a material database
    print(f"Inside the test file - {paths.data}")
    sim.volume_manager.add_material_database(paths.data / "GateMaterials.db")

    # set the world size like in the Gate macro
    world = sim.world
    world.size = [3 * m, 3 * m, 3 * m]

    # add a simple crystal volume
    crystal = sim.add_volume("Box", "crystal")
    crystal.size = [3 * mm, 3 * mm, 20 * mm]
    crystal.translation = [0 * cm, 0 * cm, 0 * cm]
    crystal.material = "BGO"
    crystal.set_production_cut("electron", 0.1 * mm)

    sim.physics_manager.physics_list_name = "G4EmStandardPhysics_option4"
    sim.physics_manager.energy_range_min = 10 * eV
    sim.physics_manager.energy_range_max = 1 * MeV
    sim.physics_manager.special_physics_constructors.G4OpticalPhysics = True

    source = sim.add_source("GenericSource", "gamma1")
    source.particle = "gamma"
    source.energy.mono = 0.511 * MeV
    source.activity = 10 * Bq
    source.direction.type = "momentum"
    source.direction.momentum = [0, 0, -1]
    source.position.translation = [0 * cm, 0 * cm, 2.2 * cm]

    # filter : remove opticalphoton
    fe = sim.add_filter("ParticleFilter", "fe")
    fe.particle = "opticalphoton"
    fe.policy = "reject"

    hc = sim.add_actor("PhaseSpaceActor", "Phase")
    hc.attached_to = crystal.name
    # hc.output = paths.output / "test075_simulation_optigan_with_random_seed.root"
    hc.attributes = [
        "Position",
        "PostPosition",
        "PrePosition",
        "ParticleName",
        "TrackCreatorProcess",
        "EventKineticEnergy",
        "KineticEnergy",
        "PDGCode",
        "ParentID",
        "EventID",
        "TrackID",
    ]

    hc.output_filename = "test075_simulation_optigan_with_random_seed_600.root"

    # add a kill actor to the crystal
    ka = sim.add_actor("KillActor", "kill_actor2")
    ka.attached_to = crystal.name
    ka.filters.append(fe)

    sim.user_hook_after_run = gate.userhooks.user_hook_dump_material_properties
    sim.run()

    # Current way to use OptiGAN
    # Call Optigan class with root output path to initialise
    # Run run_optigan method of Optigan class to get outputs
    # Outputs will be saved in contrib folder in optigan_output folder
    # optigan_input_file_name = os.path.join(sim.output_dir, hc.output_filename)
    optigan = Optigan(input_phsp_actor=hc)
    # create_output_graphs: Generates distribution graphs for each output feature.
    # Note: Enabling on high activity levels may cause memory issues.
    # Recommended to only use this for testing with low activity number.
    optigan.run_optigan(create_output_graphs=False)

    is_ok = all(t is True for t in sim.user_hook_log)
    tu.test_ok(is_ok)
