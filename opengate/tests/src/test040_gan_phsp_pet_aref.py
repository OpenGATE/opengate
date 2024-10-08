#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
import opengate.contrib.phantoms.nemaiec as gate_iec
from opengate.tests import utility

if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, "", "test040")

    # create the simulation
    sim = gate.Simulation()

    # units
    m = gate.g4_units.m
    cm = gate.g4_units.cm
    cm3 = gate.g4_units.cm3
    keV = gate.g4_units.keV
    mm = gate.g4_units.mm
    Bq = gate.g4_units.Bq
    BqmL = Bq / cm3
    sec = gate.g4_units.second
    deg = gate.g4_units.deg
    kBq = 1000 * Bq
    MBq = 1000 * kBq

    # main parameters
    sim.output_dir = paths.output
    sim.check_volumes_overlap = True
    sim.number_of_threads = 1
    sim.random_seed = 1386
    sim.output_dir = paths.output
    ac = 5e3 * BqmL / sim.number_of_threads
    sim.visu = False
    sim.visu_type = "vrml"
    colli_flag = not sim.visu
    if sim.visu:
        ac = 1 * BqmL  # per mL
        sim.number_of_threads = 1

    # world size
    world = sim.world
    world.size = [1.5 * m, 1.5 * m, 1.5 * m]
    world.material = "G4_AIR"

    # iec phantom
    iec_phantom = gate_iec.add_iec_phantom(sim)

    # c, v = gate_iec.compute_sphere_centers_and_volumes(sim, iec_phantom.name)
    # print(c)
    # print(v)

    """# add an artificial tungsten bar
    vint = sim.volume_manager.volumes["iec_interior"]
    print(vint)
    t = sim.add_volume("Box", "tung")
    t.mother = vint.name
    t.size = [3 * cm, 7 * cm, 10 * cm]
    t.translation = [-10 * cm, 5 * cm, 2 * cm]
    t.material = "G4_CADMIUM_TUNGSTATE"
    t.color = [0, 0, 1, 1]"""

    # test phase space
    phsp_sphere_surface = sim.add_volume("Sphere", "phase_space_sphere")
    phsp_sphere_surface.rmin = 215 * mm
    phsp_sphere_surface.rmax = 216 * mm
    phsp_sphere_surface.color = [1, 1, 1, 1]
    phsp_sphere_surface.material = "G4_AIR"

    # physic list
    sim.physics_manager.set_production_cut("world", "all", 1 * mm)

    # source sphere
    gate_iec.add_spheres_sources(
        sim,
        "iec",
        "source1",
        [10, 13, 17, 22, 28, 37],
        [ac * 6, ac * 5, ac * 4, ac * 3, ac * 2, ac],
        verbose=True,
    )

    # with acceptance angle (?) # FIXME
    sources = sim.source_manager.user_info_sources
    for source in sources.values():
        source.particle = "e+"
        source.energy.type = "Ga68"
        source.direction.type = "iso"

    # background source 1:10 ratio with sphere
    # bg = gate_iec.add_background_source(sim, 'iec', 'source_bg', ac / 10, verbose=True)

    # add stat actor
    stats = sim.add_actor("SimulationStatisticsActor", "Stats")
    stats.output_filename = "test040_ref_stats.txt"

    # store phsp of exiting particles (gamma only)
    phsp = sim.add_actor("PhaseSpaceActor", "phsp")
    phsp.attached_to = phsp_sphere_surface.name
    phsp.attributes = [
        "KineticEnergy",
        "PrePosition",
        "PreDirection",
        "GlobalTime",
        "TimeFromBeginOfEvent",
        "EventID",
        "EventPosition",
        "EventDirection",
        "EventKineticEnergy",
    ]
    phsp.output_filename = "test040_ref_phsp.root"
    phsp.store_absorbed_event = True
    # phsp.steps_to_store = "first"
    f = sim.add_filter("ParticleFilter", "f")
    f.particle = "gamma"
    phsp.filters.append(f)
    f = sim.add_filter("KineticEnergyFilter", "f2")
    f.energy_min = 100 * keV
    phsp.filters.append(f)

    # go
    sim.run()

    # ----------------------------------------------------------------------------------------------------------

    # check stats
    print()
    gate.exception.warning(f"Check stats")
    print(stats)
    stats_ref = utility.read_stat_file(paths.output_ref / "test040_ref_stats.txt")
    is_ok = utility.assert_stats(stats, stats_ref, 0.01)

    # 426760*2*0.8883814158496728 = 758251.3
    ref = 9523
    ae = phsp.number_of_absorbed_events
    print(ae)
    err = abs(ae - ref) / ref
    tol = 0.055
    is_ok = err < tol and is_ok
    utility.print_test(
        is_ok, f"Number of absorbed events: {ae} vs {ref} = {err * 100:.2f}%"
    )

    # No other tests here for the moment, will be used by test040_gan
    utility.test_ok(is_ok)
