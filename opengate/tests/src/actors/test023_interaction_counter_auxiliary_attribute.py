#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import numpy as np
import opengate as gate
import uproot

from opengate.actors.filters import GateFilterBuilder
from opengate.tests import utility


def run_simulation(
    paths,
    slab_thickness,
    output_filename,
    attribute_name,
    process_name,
    max_step_size=None,
):
    sim = gate.Simulation()
    sim.output_dir = paths.output
    sim.random_seed = 123456

    m = gate.g4_units.m
    cm = gate.g4_units.cm
    nm = gate.g4_units.nm
    MeV = gate.g4_units.MeV

    sim.world.size = [1 * m, 1 * m, 1 * m]
    sim.world.material = "G4_Galactic"

    slab = sim.add_volume("Box", "slab")
    slab.size = [10 * cm, 10 * cm, slab_thickness]
    slab.material = "G4_WATER"
    slab.translation = [0, 0, 0]

    plane = sim.add_volume("Box", "plane")
    plane.size = [20 * cm, 20 * cm, 1 * nm]
    plane.translation = [0, 0, slab_thickness / 2.0 + 1 * nm]
    plane.material = "G4_Galactic"

    source = sim.add_source("GenericSource", "source")
    source.particle = "gamma"
    source.energy.mono = 1 * MeV
    source.position.type = "disc"
    source.position.radius = 5 * cm
    source.position.translation = [0, 0, -5 * cm]
    source.direction.type = "momentum"
    source.direction.momentum = [0, 0, 1]
    source.n = 100000

    aux = sim.activate_auxiliary_attribute(
        "InteractionCounterAttribute",
        attribute_name,
    )
    aux.process_name = process_name

    phsp = sim.add_actor("PhaseSpaceActor", "phsp")
    phsp.attached_to = plane.name
    phsp.attributes = ["ParticleName", aux.name]
    phsp.output_filename = output_filename

    F = GateFilterBuilder()
    phsp.filter = F.ParticleName == "gamma"

    stats = sim.add_actor("SimulationStatisticsActor", "stats")
    stats.track_types_flag = True

    sim.physics_manager.physics_list_name = "G4EmStandardPhysics_option4"
    if max_step_size is not None:
        sim.physics_manager.set_max_step_size(slab.name, max_step_size)
        sim.physics_manager.set_user_limits_particles("gamma")
    sim.run(start_new_process=True)

    tree = uproot.open(phsp.get_output_path())["phsp"]
    df = tree.arrays(library="pd")
    counts = df[aux.name].to_numpy()
    return counts


if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, "", "test023")

    mm = gate.g4_units.mm

    counts_thin = run_simulation(
        paths,
        5 * mm,
        "test023_interaction_counter_thin.root",
        "InteractionCounter__compt__thin",
        "compt",
    )
    counts_thick = run_simulation(
        paths,
        10 * mm,
        "test023_interaction_counter_thick.root",
        "InteractionCounter__compt__thick",
        "compt",
    )
    counts_step_limited = run_simulation(
        paths,
        5 * mm,
        "test023_interaction_counter_step_limiter.root",
        "InteractionCounter__StepLimiter__thin",
        "StepLimiter",
        max_step_size=0.5 * mm,
    )
    counts_step_unlimited = run_simulation(
        paths,
        5 * mm,
        "test023_interaction_counter_no_step_limiter.root",
        "InteractionCounter__StepLimiter__no_limit",
        "StepLimiter",
    )

    mean_thin = np.mean(counts_thin)
    mean_thick = np.mean(counts_thick)
    ratio = mean_thick / mean_thin if mean_thin > 0 else np.nan
    mean_step_limited = np.mean(counts_step_limited)
    mean_step_unlimited = np.mean(counts_step_unlimited)

    is_ok = True

    b = len(counts_thin) > 0 and len(counts_thick) > 0
    utility.print_test(b, "Both runs produce downstream gamma phase-space entries")
    is_ok = is_ok and b

    b = mean_thin > 0 and mean_thick > 0
    utility.print_test(
        b,
        f"Both runs produce a non-zero mean interaction count ({mean_thin:.4f}, {mean_thick:.4f})",
    )
    is_ok = is_ok and b

    b = mean_thick > mean_thin
    utility.print_test(
        b,
        f"Doubling thickness increases the mean interaction count ({mean_thin:.4f} -> {mean_thick:.4f})",
    )
    is_ok = is_ok and b

    b = 1.5 < ratio < 2.5
    utility.print_test(
        b,
        f"Interaction count scales roughly with thickness (ratio={ratio:.3f})",
    )
    is_ok = is_ok and b

    b = mean_step_limited > 0
    utility.print_test(
        b,
        f"Step limiter run produces a non-zero mean StepLimiter count ({mean_step_limited:.4f})",
    )
    is_ok = is_ok and b

    b = mean_step_limited > mean_step_unlimited
    utility.print_test(
        b,
        f"Applying a step limiter increases the mean StepLimiter count ({mean_step_unlimited:.4f} -> {mean_step_limited:.4f})",
    )
    is_ok = is_ok and b

    utility.test_ok(is_ok)
