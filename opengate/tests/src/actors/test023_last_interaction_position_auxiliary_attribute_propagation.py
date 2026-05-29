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
    mm = gate.g4_units.mm
    nm = gate.g4_units.nm
    MeV = gate.g4_units.MeV

    sim.world.size = [1 * m, 1 * m, 1 * m]
    sim.world.material = "G4_Galactic"

    slab = sim.add_volume("Box", "slab")
    slab.size = [2 * cm, 2 * cm, 0.2 * mm]
    slab.material = "G4_W"
    slab.translation = [3 * cm, 0, 0]

    plane = sim.add_volume("Box", "plane")
    plane.size = [4 * cm, 4 * cm, 1 * nm]
    plane.translation = [3 * cm, 0, slab.size[2] / 2.0 + 1 * nm]
    plane.material = "G4_Galactic"

    source = sim.add_source("GenericSource", "source")
    source.particle = "e-"
    source.energy.mono = 6 * MeV
    source.position.type = "disc"
    source.position.radius = 0.2 * mm
    source.position.translation = [3 * cm, 0, -1 * cm]
    source.direction.type = "momentum"
    source.direction.momentum = [0, 0, 1]
    source.n = 50000

    aux_no_prop = sim.activate_auxiliary_attribute(
        "LastInteractionPositionInVolumeAttribute",
        "LastInteractionPositionNoProp__slab",
    )
    aux_no_prop.volume_name = slab.name
    aux_no_prop.propagate_from_parent_track = False

    aux_prop = sim.activate_auxiliary_attribute(
        "LastInteractionPositionInVolumeAttribute",
        "LastInteractionPositionProp__slab",
    )
    aux_prop.volume_name = slab.name
    aux_prop.propagate_from_parent_track = True

    phsp = sim.add_actor("PhaseSpaceActor", "phsp")
    phsp.attached_to = plane.name
    phsp.attributes = ["ParticleName", "ParentID", aux_no_prop.name, aux_prop.name]
    phsp.output_filename = "test023_last_interaction_position_propagation.root"

    stats = sim.add_actor("SimulationStatisticsActor", "stats")
    stats.track_types_flag = True

    sim.physics_manager.physics_list_name = "G4EmStandardPhysics_option4"
    sim.run()

    tree = uproot.open(phsp.get_output_path())["phsp"]
    df = tree.arrays(library="pd")

    particle_name = df["ParticleName"].to_numpy()
    parent_id = df["ParentID"].to_numpy()

    no_prop_x = df[f"{aux_no_prop.name}_X"].to_numpy()
    no_prop_y = df[f"{aux_no_prop.name}_Y"].to_numpy()
    no_prop_z = df[f"{aux_no_prop.name}_Z"].to_numpy()

    prop_x = df[f"{aux_prop.name}_X"].to_numpy()
    prop_y = df[f"{aux_prop.name}_Y"].to_numpy()
    prop_z = df[f"{aux_prop.name}_Z"].to_numpy()

    # Focus on secondary gammas born in the slab and immediately scored on the
    # downstream plane. In vacuum after the slab, finite values should mostly
    # come from inheritance rather than new interactions.
    secondary_gamma = (particle_name == "gamma") & (parent_id > 0)

    no_prop_finite = (
        np.isfinite(no_prop_x) & np.isfinite(no_prop_y) & np.isfinite(no_prop_z)
    )
    prop_finite = np.isfinite(prop_x) & np.isfinite(prop_y) & np.isfinite(prop_z)

    half_size_x = slab.size[0] / 2.0
    half_size_y = slab.size[1] / 2.0
    half_size_z = slab.size[2] / 2.0
    center_x, center_y, center_z = slab.translation

    inside_prop = (
        (prop_x >= center_x - half_size_x)
        & (prop_x <= center_x + half_size_x)
        & (prop_y >= center_y - half_size_y)
        & (prop_y <= center_y + half_size_y)
        & (prop_z >= center_z - half_size_z)
        & (prop_z <= center_z + half_size_z)
    )

    is_ok = True

    b = np.any(secondary_gamma)
    utility.print_test(
        b,
        "Phase space contains secondary gammas crossing the downstream plane",
    )
    is_ok = is_ok and b

    prop_count = np.count_nonzero(prop_finite[secondary_gamma])
    no_prop_count = np.count_nonzero(no_prop_finite[secondary_gamma])

    b = prop_count > 0
    utility.print_test(
        b,
        "Propagated attribute yields finite last interaction positions for secondary gammas",
    )
    is_ok = is_ok and b

    b = np.all(inside_prop[secondary_gamma & prop_finite])
    utility.print_test(
        b,
        "Propagated secondary-gamma positions lie inside the interaction slab",
    )
    is_ok = is_ok and b

    b = no_prop_count < prop_count
    utility.print_test(
        b,
        f"Propagation increases the number of finite inherited positions ({no_prop_count} vs {prop_count})",
    )
    is_ok = is_ok and b

    utility.test_ok(is_ok)
