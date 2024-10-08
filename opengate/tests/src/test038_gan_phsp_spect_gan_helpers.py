#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import uproot
import numpy as np
import matplotlib.pyplot as plt
import os
import opengate as gate
import opengate.contrib.spect.ge_discovery_nm670 as gate_spect
import opengate.contrib.phantoms.nemaiec as gate_iec
import gatetools.phsp as phsp
from opengate.tests import utility


class GANTest:
    def __init__(self, spheres_activity_ratio, spheres_centers, spheres_radius, rs):
        # will store all conditional info (position, direction)
        # (not needed, only for test)
        self.all_cond = None
        self.spheres_activity_ratio = spheres_activity_ratio
        self.spheres_centers = spheres_centers
        self.spheres_radius = spheres_radius
        self.rs = rs

    def generate_condition(self, n):
        n_samples = gate_iec.get_n_samples_from_ratio(n, self.spheres_activity_ratio)
        cond = gate_iec.generate_pos_dir_spheres(
            self.spheres_centers,
            self.spheres_radius,
            n_samples,
            shuffle=True,
            rs=self.rs,
        )

        if self.all_cond is None:
            self.all_cond = cond
        else:
            self.all_cond = np.column_stack((self.all_cond, cond))

        return cond


def create_simulation(sim, paths, colli="lehr"):
    # units
    m = gate.g4_units.m
    cm = gate.g4_units.cm
    cm3 = gate.g4_units.cm3
    keV = gate.g4_units.keV
    mm = gate.g4_units.mm
    Bq = gate.g4_units.Bq
    BqmL = Bq / cm3

    # main parameters
    sim.check_volumes_overlap = True
    sim.random_seed = 4123456
    # ac = 1e6 * BqmL
    ac = 3e3 * BqmL / sim.number_of_threads
    sim.visu = False
    # sim.running_verbose_level = gate.EVENT
    # sim.g4_verbose = True
    sim.output_dir = paths.output

    # world size
    world = sim.world
    world.size = [1.5 * m, 1.5 * m, 1.5 * m]
    world.material = "G4_AIR"

    # cylinder of the phase space, for visualisation only
    """cyl = sim.add_volume('Sphere', 'phase_space_cylinder')
    cyl.rmin = 210 * mm
    cyl.rmax = 211 * mm
    cyl.color = [1, 1, 1, 1]
    cyl.material = 'G4_AIR'"""

    # test phase space to check with reference
    phase_space_sphere = sim.add_volume("Sphere", "phase_space_sphere")
    phase_space_sphere.rmin = 212 * mm
    phase_space_sphere.rmax = 213 * mm
    phase_space_sphere.color = [1, 1, 1, 1]
    phase_space_sphere.material = "G4_AIR"

    # spect head
    distance = 30 * cm
    psd = 6.11 * cm
    p = [0, 0, -(distance + psd)]
    spect1, colli, crystal = gate_spect.add_spect_head(
        sim, "spect1", collimator_type=colli, debug=sim.visu
    )
    spect1.translation, spect1.rotation = gate.geometry.utility.get_transform_orbiting(
        p, "x", 180
    )

    # physic list
    sim.physics_manager.set_production_cut("world", "all", 1 * mm)

    # activity parameters
    spheres_diam = [10, 13, 17, 22, 28, 37]
    spheres_activity_concentration = [ac * 6, ac * 5, ac * 4, ac * 3, ac * 2, ac]

    # initialisation for conditional
    spheres_radius = [x / 2.0 for x in spheres_diam]
    (
        spheres_centers,
        spheres_volumes,
    ) = gate_iec.get_default_sphere_centers_and_volumes_old()
    spheres_activity_ratio = []
    spheres_activity = []
    for diam, ac, volume, center in zip(
        spheres_diam, spheres_activity_concentration, spheres_volumes, spheres_centers
    ):
        activity = ac * volume
        print(
            f"Sphere {diam}: {str(center):<30} {volume / cm3:7.3f} cm3 "
            f"{activity / Bq:7.0f} Bq  {ac / BqmL:7.1f} BqmL"
        )
        spheres_activity.append(activity)

    total_activity = sum(spheres_activity)
    print(f"Total activity {total_activity / Bq:.0f} Bq")
    for activity in spheres_activity:
        spheres_activity_ratio.append(activity / total_activity)
    print("Activity ratio ", spheres_activity_ratio, sum(spheres_activity_ratio))

    # unique (reproducible) random generator
    rs = gate.utility.get_rnd_seed(123456)

    # GAN source
    gsource = sim.add_source("GANSource", "gaga")
    gsource.particle = "gamma"
    # no phantom, we consider attached to the world at origin
    # gsource.mother = f'{iec_phantom.name}_interior'
    gsource.activity = total_activity
    gsource.pth_filename = paths.gate / "pth2" / "test001_GP_0GP_10_50000.pth"
    gsource.position_keys = ["PrePosition_X", "PrePosition_Y", "PrePosition_Z"]
    gsource.backward_distance = 5 * cm
    gsource.direction_keys = ["PreDirection_X", "PreDirection_Y", "PreDirection_Z"]
    gsource.energy_key = "KineticEnergy"
    # gsource.energy_threshold = 0.001 * keV
    gsource.energy_min_threshold = 10 * keV
    # gsource.skip_policy = "SkipEvents"
    # SkipEvents is a bit faster than Energy zero,
    # but it changes the nb of events,so force ZeroEnergy
    gsource.skip_policy = "ZeroEnergy"
    gsource.weight_key = None
    gsource.time_key = "TimeFromBeginOfEvent"
    gsource.relative_timing = True
    gsource.batch_size = 5e4
    gsource.verbose_generator = True
    gsource.gpu_mode = (
        utility.get_gpu_mode_for_tests()
    )  # should be "auto" but "cpu" for macOS github actions to avoid mps errors

    # GANSourceConditionalGenerator manages the conditional GAN
    # GANTest manages the generation of the conditions, we use a class here to store the total
    # list of conditions (only needed for the test)
    condition_generator = GANTest(
        spheres_activity_ratio, spheres_centers, spheres_radius, rs
    )
    gen = gate.sources.gansources.GANSourceConditionalGenerator(
        gsource, condition_generator.generate_condition
    )
    gsource.generator = gen

    # it is possible to use acceptance angle. Not done here to check exiting phsp
    # gsource.direction.acceptance_angle.volumes = [spect1.name]
    # gsource.direction.acceptance_angle.intersection_flag = True

    # add stat actor
    stat = sim.add_actor("SimulationStatisticsActor", "Stats")
    stat.output_filename = "test038_gan_stats.txt"

    # add default digitizer (it is easy to change parameters if needed)
    gate_spect.add_simplified_digitizer_tc99m(
        sim, "spect1_crystal", "test038_gan_proj.mhd"
    )
    # gate_spect.add_ge_nm670_spect_simplified_digitizer(sim, 'spect2_crystal', paths.output / 'test033_proj_2.mhd')
    singles_actor = sim.actor_manager.get_actor(f"Singles_spect1_crystal")
    singles_actor.output_filename = "test038_gan_singles.root"

    # motion of the spect, create also the run time interval
    """heads = [spect1]  # [spect1, spect2]

    # create a list of run (total = 1 second)
    n = 1
    sim.run_timing_intervals = gate.range_timing(0, 1 * sec, n)

    for head in heads:
        motion = sim.add_actor('MotionVolumeActor', f'Move_{head.name}')
        motion.mother = head.name
        motion.translations, motion.rotations = \
            gate.volume_orbiting_transform('x', 0, 180, n, head.translation, head.rotation)
        motion.priority = 5"""

    phsp_actor = sim.add_actor("PhaseSpaceActor", "phsp")
    phsp_actor.attached_to = phase_space_sphere.name
    phsp_actor.attributes = [
        "KineticEnergy",
        "PrePosition",
        "PreDirection",
        "GlobalTime",
        "EventPosition",
        "EventDirection",
        "EventKineticEnergy",
    ]
    phsp_actor.output_filename = "test038_gan_phsp.root"

    return condition_generator


def analyze_results(sim, paths, all_cond):
    phsp_actor = sim.get_actor("phsp")
    print(phsp_actor)

    # print stats
    print()
    gate.exception.warning(f"Check stats")
    s = sim.get_source_user_info("gaga")
    print(f"Source, nb of skipped particles (absorbed) : {s.fTotalSkippedEvents}")
    print(f"Source, nb of zeros   particles (absorbed) : {s.fTotalZeroEvents}")

    stats = sim.get_actor("Stats")
    print(stats)
    stats.counts.events += s.fTotalSkippedEvents
    stats_ref = utility.read_stat_file(paths.output_ref / "test038_ref_stats.txt")
    r = (stats_ref.counts.steps - stats.counts.steps) / stats_ref.counts.steps
    print(f"Steps cannot be compared => was {stats.counts.steps}, {r:.2f}%")
    stats.counts.steps = stats_ref.counts.steps
    if s.fTotalSkippedEvents > 0:
        print(f"Tracks cannot be compared => was {stats.counts.tracks}")
        stats.counts.tracks = stats_ref.counts.tracks

    stats.counts.runs = 1  # force for MT
    is_ok = utility.assert_stats(stats, stats_ref, 0.10)

    # save conditional for checking with reference cond
    keys = [
        "EventPosition_X",
        "EventPosition_Y",
        "EventPosition_Z",
        "EventDirection_X",
        "EventDirection_Y",
        "EventDirection_Z",
    ]
    phsp.save_npy(paths.output / "test038_gan_phsp_cond.npy", all_cond, keys)

    # ----------------------------------------------------------------------------------------------
    # compare conditional
    # less particle in the ref because conditional data are stored
    # when exit (not absorbed)
    print()
    gate.exception.warning(f"Check conditions (position, direction)")
    root_ref = (
        paths.output_ref / "test038_ref_phsp.root"
    )  # looking the previous generated
    hits1 = uproot.open(root_ref)
    branch = hits1.keys()[0]
    print("Branch name:", branch)
    hits1 = hits1[branch]
    hits1_n = hits1.num_entries
    hits1 = hits1.arrays(library="numpy")
    root_gan = paths.output / "test038_gan_phsp_cond.npy"
    hits2, hits2_keys, hits2_n = phsp.load(root_gan)
    tols = [10.0] * len(keys)
    tols[keys.index("EventPosition_X")] = 0.3
    tols[keys.index("EventPosition_Y")] = 0.5
    tols[keys.index("EventPosition_Z")] = 0.3
    tols[keys.index("EventDirection_X")] = 0.02
    tols[keys.index("EventDirection_Y")] = 0.02
    tols[keys.index("EventDirection_Z")] = 0.03
    scalings = [1] * len(keys)
    is_ok = (
        utility.compare_trees(
            hits1,
            list(hits1.keys()),
            hits2,
            list(hits2_keys),
            keys,
            keys,
            tols,
            scalings,
            scalings,
            True,
        )
        and is_ok
    )
    # figure
    img_filename = paths.output / "test038_cond.png"
    plt.suptitle(
        f"Values: ref {os.path.basename(root_ref)} {os.path.basename(root_gan)} "
        f"-> {hits1_n} vs {hits2_n}"
    )
    plt.savefig(img_filename)
    print(f"Figure in {img_filename}")

    # ----------------------------------------------------------------------------------------------
    # compare output phsp
    """
        This is *not* a very good pth for the moment, we set a high tolerance.
    """
    print()
    gate.exception.warning(f"Check output phsp")
    ref_file = paths.output_ref / "test038_ref_phsp.root"
    hc_file = phsp_actor.get_output_path()
    checked_keys = [
        "GlobalTime",
        "KineticEnergy",
        "PrePosition_X",
        "PrePosition_Y",
        "PrePosition_Z",
        "PreDirection_X",
        "PreDirection_Y",
        "PreDirection_Z",
    ]
    scalings = [1.0] * len(checked_keys)
    scalings[checked_keys.index("GlobalTime")] = 1e-9  # time in ns
    tols = [10.0] * len(checked_keys)
    tols[checked_keys.index("GlobalTime")] = 0.2
    tols[checked_keys.index("KineticEnergy")] = 0.002
    tols[checked_keys.index("PrePosition_X")] = 7
    tols[checked_keys.index("PrePosition_Y")] = 4
    tols[checked_keys.index("PrePosition_Z")] = 4
    tols[checked_keys.index("PreDirection_X")] = 0.02
    tols[checked_keys.index("PreDirection_Y")] = 0.02
    tols[checked_keys.index("PreDirection_Z")] = 0.02
    print(scalings, tols)
    is_ok = (
        utility.compare_root3(
            ref_file,
            hc_file,
            "phsp",
            "phsp",
            checked_keys,
            checked_keys,
            tols,
            scalings,
            scalings,
            paths.output / "test038_phsp.png",
        )
        and is_ok
    )

    # ----------------------------------------------------------------------------------------------
    # compare hits
    print()
    gate.exception.warning(f"Check singles -> NOT YET (too low statistics)")

    """ref_file = paths.output / 'test038_ref_singles.root'
    hc_file = singles_actor.output
    checked_keys = ['GlobalTime', 'TotalEnergyDeposit', 'PostPosition_X', 'PostPosition_Y', 'PostPosition_Z']
    scalings = [1.0] * len(checked_keys)
    scalings[checked_keys.index('GlobalTime')] = 1e-9  # time in ns
    tols[checked_keys.index('GlobalTime')] = 0.2
    tols[checked_keys.index('TotalEnergyDeposit')] = 10
    tols[checked_keys.index('PostPosition_X')] = 100
    tols[checked_keys.index('PostPosition_Y')] = 100
    tols[checked_keys.index('PostPosition_Z')] = 100
    print(scalings, tols)
    is_ok = utility.compare_root3(ref_file, hc_file, "Singles_spect1_crystal", "Singles_spect1_crystal",
                              checked_keys, checked_keys, tols, scalings, scalings,
                              paths.output / 'test038_singles.png', hits_tol=100) and is_ok
    """
    # ----------------------------------------------------------------------------------------------

    # this is the end, my friend
    # gate.delete_run_manager_if_needed(sim)
    utility.test_ok(is_ok)
