#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import numpy as np
import opengate as gate
import uproot

from opengate.tests import utility


if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, "", "test023")

    sim = gate.Simulation()
    sim.output_dir = paths.output

    m = gate.g4_units.m
    cm = gate.g4_units.cm
    nm = gate.g4_units.nm
    MeV = gate.g4_units.MeV

    sim.world.size = [1 * m, 1 * m, 1 * m]
    sim.world.material = "G4_Galactic"

    water_box = sim.add_volume("Box", "water_box")
    water_box.size = [10 * cm, 10 * cm, 5 * cm]
    water_box.material = "G4_WATER"
    water_box.translation = [0, 0, 0]

    plane = sim.add_volume("Box", "plane")
    plane.size = [20 * cm, 20 * cm, 1 * nm]
    plane.translation = [0, 0, 4 * cm]
    plane.material = "G4_Galactic"

    source = sim.add_source("GenericSource", "source")
    source.particle = "gamma"
    source.energy.mono = 1 * MeV
    source.position.type = "disc"
    source.position.radius = 1 * cm
    source.position.translation = [0, 0, -6 * cm]
    source.direction.type = "momentum"
    source.direction.momentum = [0, 0, 1]
    source.n = 5000

    aux_process = sim.activate_auxiliary_attribute(
        "LastProcessDefinedStepInVolumeAttribute",
        "LastProcess__water_box",
    )
    aux_process.volume_name = water_box.name

    aux_position = sim.activate_auxiliary_attribute(
        "LastInteractionPositionInVolumeAttribute",
        "LastInteractionPosition__water_box",
    )
    aux_position.volume_name = water_box.name

    phsp = sim.add_actor("PhaseSpaceActor", "phsp")
    phsp.attached_to = plane.name
    phsp.attributes = [aux_process.name, aux_position.name]
    phsp.output_filename = "test023_last_interaction_position.root"

    stats = sim.add_actor("SimulationStatisticsActor", "stats")
    stats.track_types_flag = True

    sim.physics_manager.physics_list_name = "G4EmStandardPhysics_option4"
    sim.run()

    tree = uproot.open(phsp.get_output_path())["phsp"]
    df = tree.arrays(library="pd")

    process_values = df[aux_process.name].to_numpy()
    pos_x = df[f"{aux_position.name}_X"].to_numpy()
    pos_y = df[f"{aux_position.name}_Y"].to_numpy()
    pos_z = df[f"{aux_position.name}_Z"].to_numpy()

    has_interaction = process_values != "Transportation"
    no_interaction = ~has_interaction

    half_size_x = water_box.size[0] / 2.0
    half_size_y = water_box.size[1] / 2.0
    half_size_z = water_box.size[2] / 2.0
    center_x, center_y, center_z = water_box.translation

    inside_x = (pos_x >= center_x - half_size_x) & (pos_x <= center_x + half_size_x)
    inside_y = (pos_y >= center_y - half_size_y) & (pos_y <= center_y + half_size_y)
    inside_z = (pos_z >= center_z - half_size_z) & (pos_z <= center_z + half_size_z)

    pos_is_nan = np.isnan(pos_x) & np.isnan(pos_y) & np.isnan(pos_z)
    pos_is_finite = np.isfinite(pos_x) & np.isfinite(pos_y) & np.isfinite(pos_z)

    is_ok = True

    b = np.any(has_interaction)
    utility.print_test(
        b,
        "Phase space contains tracks with a non-Transportation last process in the volume",
    )
    is_ok = is_ok and b

    b = np.any(no_interaction)
    utility.print_test(
        b,
        "Phase space contains tracks with no stored interaction in the volume",
    )
    is_ok = is_ok and b

    b = np.all(pos_is_finite[has_interaction])
    utility.print_test(
        b,
        "Tracks with a stored last process have finite last interaction positions",
    )
    is_ok = is_ok and b

    b = np.all((inside_x & inside_y & inside_z)[has_interaction])
    utility.print_test(
        b,
        "Tracks with a stored last process have last interaction positions inside the target volume",
    )
    is_ok = is_ok and b

    b = np.all(pos_is_nan[no_interaction])
    utility.print_test(
        b,
        "Tracks with no stored interaction return NaN for the last interaction position",
    )
    is_ok = is_ok and b

    utility.test_ok(is_ok)
