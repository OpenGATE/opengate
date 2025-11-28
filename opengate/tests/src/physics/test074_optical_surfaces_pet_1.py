#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
import opengate.tests.utility as tu

if __name__ == "__main__":
    paths = tu.get_default_test_paths(__file__, "", "test074")

    # create simulation
    sim = gate.Simulation()
    sim.g4_verbose = True
    sim.output_dir = paths.output

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

    # add a surface
    # Users can specify their own path surface properties file by
    # sim.physics_manager.surface_properties_file = (
    #     "/Users/data_machine/Work/pyGate/opengate/opengate/data/SurfaceProperties.xml"
    # )
    # By default, Gate uses the file opengate/data/SurfaceProperties.xml

    # Syntax to add optical surface between two volumes
    # add_optical_surface("volume_from","volume_to", "surface_name")
    # keywords can be used for clarity
    # the name of the GATE optical surface is created automatically
    opt_surf_world_crystal = sim.physics_manager.add_optical_surface(
        volume_from="world",
        volume_to="crystal",
        g4_surface_name="polished_teflon_wrapped",
    )
    opt_surf_crystal_world = sim.physics_manager.add_optical_surface(
        "crystal", "world", "Rough_LUT"
    )

    print(sim.physics_manager.dump_optical_surfaces())

    # Examples -
    # sim.add_optical_surface("OpticalSystem", "Crystal1","PolishedTeflon_LUT")
    # sim.add_optical_surface("Crystal1", "OpticalSystem", "PolishedTeflon_LUT")
    # sim.add_optical_surface("Greasepixel", "Crystal1", "Polished_LUT")
    # sim.add_optical_surface("Crystal1", "Greasepixel", "Polished_LUT")
    # sim.add_optical_surface("Greasepixel", "pixel", "Detector_LUT")
    # sim.add_optical_surface("pixel", "Greasepixel", "Detector_LUT")

    # change physics
    # For the generation of Cerenkov, physics_list_name must
    # be set to G4EmStandardPhysics_option4 and production cuts
    # of electron must be set to 0.1 mm (Reason unknown)
    # Reference - https://opengate.readthedocs.io/en/latest/generating_and_tracking_optical_photons.html
    sim.physics_manager.physics_list_name = "G4EmStandardPhysics_option4"
    sim.physics_manager.set_production_cut("crystal", "electron", 0.1 * mm)
    sim.physics_manager.energy_range_min = 10 * eV
    sim.physics_manager.energy_range_max = 1 * MeV
    sim.physics_manager.special_physics_constructors.G4OpticalPhysics = True

    # Users can specify their own path optical properties file by
    # sim.physics_manager.optical_properties_file = PATH_TO_FILE
    # By default, Gate uses the file opengate/data/OpticalProperties.xml

    # Change source
    source = sim.add_source("GenericSource", "gamma1")
    source.particle = "gamma"
    source.energy.mono = 0.511 * MeV
    source.activity = 10 * Bq
    source.direction.type = "momentum"
    source.direction.momentum = [0, 0, -1]
    source.position.translation = [0 * cm, 0 * cm, 2.2 * cm]

    # add phase actor
    phase = sim.add_actor("PhaseSpaceActor", "Phase")
    phase.attached_to = crystal
    phase.attributes = [
        "Position",
        "PostPosition",
        "PrePosition",
        "ParticleName",
        "TrackCreatorProcess",
        "EventKineticEnergy",
        "KineticEnergy",
        "PDGCode",
    ]
    phase.output_filename = "test070_pet_surfaces_1.root"

    sim.user_hook_after_run = gate.userhooks.user_hook_dump_material_properties
    sim.run()

    is_ok = all(t is True for t in sim.user_hook_log)
    tu.test_ok(is_ok)
