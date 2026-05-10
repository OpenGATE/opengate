#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
from opengate.tests import utility
from opengate.actors.filters import GateFilterBuilder
import uproot
import numpy as np


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

    aux = sim.add_auxiliary_attribute(
        "ProcessDefinedStepInVolumeAttribute",
        "ProcessDefinedStep__compt__water_box",
    )
    aux.process_name = "compt"
    aux.volume_name = water_box.name

    phsp_all = sim.add_actor("PhaseSpaceActor", "phsp_all")
    phsp_all.attached_to = plane.name
    phsp_all.attributes = ["KineticEnergy", aux.name]
    phsp_all.output_filename = "test023_aux_filter_all.root"

    F = GateFilterBuilder()
    phsp_filtered = sim.add_actor("PhaseSpaceActor", "phsp_filtered")
    phsp_filtered.attached_to = plane.name
    phsp_filtered.attributes = ["KineticEnergy", aux.name]
    phsp_filtered.output_filename = "test023_aux_filter_selected.root"
    phsp_filtered.filter = F(aux.name) > 0

    stats = sim.add_actor("SimulationStatisticsActor", "stats")
    stats.track_types_flag = True

    sim.physics_manager.physics_list_name = "G4EmStandardPhysics_option4"
    sim.run()

    tree_all = uproot.open(phsp_all.get_output_path())["phsp_all"]
    tree_filtered = uproot.open(phsp_filtered.get_output_path())["phsp_filtered"]

    df_all = tree_all.arrays(library="pd")
    df_filtered = tree_filtered.arrays(library="pd")

    aux_branch = f"{aux.name}"
    aux_all = df_all[aux_branch].to_numpy()
    aux_filtered = df_filtered[aux_branch].to_numpy()

    expected_selected = np.sum(aux_all > 0)

    is_ok = True
    b = len(df_filtered) > 0
    utility.print_test(b, "Filtered phase space contains entries")
    is_ok = is_ok and b

    b = len(df_filtered) < len(df_all)
    utility.print_test(b, "Filter rejects at least some entries")
    is_ok = is_ok and b

    b = np.all(aux_filtered > 0)
    utility.print_test(b, "All filtered auxiliary counts are strictly positive")
    is_ok = is_ok and b

    b = len(df_filtered) == expected_selected
    utility.print_test(
        b,
        f"Filtered entry count matches auxiliary predicate ({len(df_filtered)} vs {expected_selected})",
    )
    is_ok = is_ok and b

    utility.test_ok(is_ok)
