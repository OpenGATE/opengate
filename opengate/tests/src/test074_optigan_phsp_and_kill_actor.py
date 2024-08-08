# This file implements the phsp and kill actor to extract
# optical photon data

import opengate as gate
import opengate.tests.utility as tu

from optigan_helpers import OptiganHelpers


if __name__ == "__main__":
    paths = tu.get_default_test_paths(__file__, "")

    # create simulation
    sim = gate.Simulation()
    sim.g4_verbose = True

    # units
    m = gate.g4_units.m
    cm = gate.g4_units.cm
    mm = gate.g4_units.mm
    eV = gate.g4_units.eV
    MeV = gate.g4_units.MeV
    Bq = gate.g4_units.Bq

    # add a material database
    sim.volume_manager.add_material_database(paths.data / "GateMaterials.db")

    # set the world size like in the Gate macro
    sim.world.size = [3 * m, 3 * m, 3 * m]

    # add a simple crystal volume
    crystal = sim.add_volume("Box", "crystal")
    crystal.size = [3 * mm, 3 * mm, 20 * mm]
    crystal.translation = [0 * cm, 0 * cm, 0 * cm]
    crystal.material = "BGO"

    opt_surf_world_crystal = sim.physics_manager.add_optical_surface(
        volume_from="world",
        volume_to="crystal",
        g4_surface_name="polished_teflon_wrapped",
    )

    opt_surf_crystal_world = sim.physics_manager.add_optical_surface(
        "crystal", "world", "Rough_LUT"
    )

    sim.physics_manager.physics_list_name = "G4EmStandardPhysics_option4"
    sim.physics_manager.set_production_cut("crystal", "electron", 0.1 * mm)
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
    fe.policy = "discard"

    # add a phase space actor to the crystal
    phase = sim.add_actor("PhaseSpaceActor", "Phase")
    phase.mother = crystal.name
    phase.output = paths.output / "test074_optigan_phsp_and_kill_actor.root"
    phase.attributes = [
        "Position",
        "PrePosition",
        "ParticleName",
        "ParentID",
        "TrackID",
        "TrackCreatorProcess",
        "EventKineticEnergy",
        "KineticEnergy",
        "PDGCode",
    ]

    # add a kill actor to the crystal 
    ka = sim.add_actor("KillActor", "kill_actor2")
    ka.mother = crystal.name
    ka.filters.append(fe)

    # assign more priority to phase 
    phase.priority = ka.priority + 10

    sim.user_hook_after_run = gate.userhooks.user_hook_dump_material_properties
    sim.run()

    optigan_input = OptiganHelpers(phase.output)
    print(optigan_input.get_optigan_input())

    is_ok = all(t is True for t in sim.output.hook_log)
    tu.test_ok(is_ok)
