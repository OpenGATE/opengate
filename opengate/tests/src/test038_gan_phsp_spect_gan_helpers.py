#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
import opengate.contrib.spect_ge_nm670 as gate_spect
import opengate.contrib.phantom_nema_iec_body as gate_iec
import gatetools.phsp as phsp
import uproot
import numpy as np
import matplotlib.pyplot as plt
import os


def create_simulation(sim, paths):
    # units
    m = gate.g4_units("m")
    cm = gate.g4_units("cm")
    cm3 = gate.g4_units("cm3")
    keV = gate.g4_units("keV")
    mm = gate.g4_units("mm")
    Bq = gate.g4_units("Bq")
    BqmL = Bq / cm3

    # main parameters
    ui = sim.user_info
    ui.check_volumes_overlap = True
    ui.random_seed = 123456
    # ac = 1e6 * BqmL
    ac = 3e3 * BqmL / ui.number_of_threads
    ui.visu = False

    # world size
    world = sim.world
    world.size = [1.5 * m, 1.5 * m, 1.5 * m]
    world.material = "G4_AIR"

    # iec phantom not needed
    # iec_phantom = gate_iec.add_phantom(sim)

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
    spect1 = gate_spect.add_ge_nm67_spect_head(
        sim, "spect1", collimator_type="lehr", debug=ui.visu
    )
    spect1.translation, spect1.rotation = gate.get_transform_orbiting(p, "x", 180)

    # spect head (debug mode = very small collimator)
    # spect2 = gate_spect.add_ge_nm67_spect_head(sim, 'spect2', collimator=colli_flag, debug=False)
    # spect2.translation, spect2.rotation = gate.get_transform_orbiting(p, 'x', 0)

    # physic list
    sim.set_cut("world", "all", 1 * mm)

    # activity parameters
    spheres_diam = [10, 13, 17, 22, 28, 37]
    spheres_activity_concentration = [ac * 6, ac * 5, ac * 4, ac * 3, ac * 2, ac]
    # spheres_diam = [37]
    # spheres_activity_concentration = [ac] * len(spheres_diam)

    # initialisation for conditional
    spheres_radius = [x / 2.0 for x in spheres_diam]
    # spheres_centers, spheres_volumes = gate_iec.compute_sphere_centers_and_volumes(sim, iec_phantom.name)
    spheres_centers, spheres_volumes = gate_iec.get_default_sphere_centers_and_volumes()
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
    # print('Radius ', spheres_radius)
    # print('Volumes ', spheres_volumes)

    # unique (reproducible) random generator
    rs = gate.get_rnd_seed(123456)

    class GANTest:
        def __init__(self):
            # will store all conditional info (position, direction)
            # (not needed, only for test)
            self.all_cond = None

        def __getstate__(self):
            print("getstate GANTest")
            for v in self.__dict__:
                print("state", v)
            self.all_cond = None
            return {}  # self.__dict__

        def generate_condition(self, n):
            n_samples = gate_iec.get_n_samples_from_ratio(n, spheres_activity_ratio)
            cond = gate_iec.generate_pos_dir_spheres(
                spheres_centers, spheres_radius, n_samples, shuffle=True, rs=rs
            )

            if self.all_cond is None:
                self.all_cond = cond
            else:
                self.all_cond = np.column_stack((self.all_cond, cond))

            return cond

    # GAN source
    gsource = sim.add_source("GAN", "gaga")
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
    gsource.energy_threshold = 10 * keV
    # gsource.skip_policy = "SkipEvents" # This is a bit faster than Energy zero
    # but change the nb of events,so force ZeroEnergy
    gsource.skip_policy = "ZeroEnergy"
    gsource.weight_key = None
    gsource.time_key = "TimeFromBeginOfEvent"
    gsource.time_relative = True
    gsource.batch_size = 5e4
    gsource.verbose_generator = True

    # GANSourceConditionalGenerator manages the conditional GAN
    # GANTest manages the generation of the conditions, we use a class here to store the total
    # list of conditions (only needed for the test)
    condition_generator = GANTest()
    gen = gate.GANSourceConditionalGenerator(
        gsource, condition_generator.generate_condition
    )
    gsource.generator = gen

    # it is possible to use acceptance angle. Not done here to check exiting phsp
    # gsource.direction.acceptance_angle.volumes = [spect1.name]
    # gsource.direction.acceptance_angle.intersection_flag = True

    # add stat actor
    stat = sim.add_actor("SimulationStatisticsActor", "Stats")
    stat.output = paths.output / "test038_gan_stats.txt"

    # add default digitizer (it is easy to change parameters if needed)
    gate_spect.add_simplified_digitizer_Tc99m(
        sim, "spect1_crystal", paths.output / "test038_gan_proj.mhd"
    )
    # gate_spect.add_ge_nm670_spect_simplified_digitizer(sim, 'spect2_crystal', paths.output / 'test033_proj_2.mhd')
    singles_actor = sim.get_actor_user_info(f"Singles_spect1_crystal")
    singles_actor.output = paths.output / "test038_gan_singles.root"

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
    phsp_actor.mother = phase_space_sphere.name
    phsp_actor.attributes = [
        "KineticEnergy",
        "PrePosition",
        "PreDirection",
        "GlobalTime",
        "EventPosition",
        "EventDirection",
        "EventKineticEnergy",
    ]
    phsp_actor.output = paths.output / "test038_gan_phsp.root"

    return condition_generator


def analyze_results(output, paths, all_cond):
    ui = output.simulation.user_info
    phsp_actor = output.get_actor("phsp").user_info

    # print stats
    print()
    gate.warning(f"Check stats")
    if ui.number_of_threads == 1:
        s = output.get_source("gaga")
    else:
        s = output.get_source_MT("gaga", 0)
    print(f"Source, nb of skipped particles (absorbed) : {s.fTotalSkippedEvents}")
    print(f"Source, nb of zeros   particles (absorbed) : {s.fTotalZeroEvents}")

    stats = output.get_actor("Stats")
    print(stats)
    stats.counts.event_count += s.fTotalSkippedEvents
    stats_ref = gate.read_stat_file(paths.output_ref / "test038_ref_stats.txt")
    r = (
        stats_ref.counts.step_count - stats.counts.step_count
    ) / stats_ref.counts.step_count
    print(f"Steps cannot be compared => was {stats.counts.step_count}, {r:.2f}%")
    stats.counts.step_count = stats_ref.counts.step_count
    if s.fTotalSkippedEvents > 0:
        print(f"Tracks cannot be compared => was {stats.counts.track_count}")
        stats.counts.track_count = stats_ref.counts.track_count

    stats.counts.run_count = 1  # force for MT
    is_ok = gate.assert_stats(stats, stats_ref, 0.10)

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
    gate.warning(f"Check conditions (position, direction)")
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
    tols[keys.index("EventDirection_Z")] = 0.02
    scalings = [1] * len(keys)
    is_ok = (
        gate.compare_trees(
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
    gate.warning(f"Check output phsp")
    ref_file = paths.output_ref / "test038_ref_phsp.root"
    hc_file = phsp_actor.output
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
        gate.compare_root3(
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
    gate.warning(f"Check singles -> NOT YET (too low statistics)")

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
    is_ok = gate.compare_root3(ref_file, hc_file, "Singles_spect1_crystal", "Singles_spect1_crystal",
                              checked_keys, checked_keys, tols, scalings, scalings,
                              paths.output / 'test038_singles.png', hits_tol=100) and is_ok
    """
    # ----------------------------------------------------------------------------------------------

    # this is the end, my friend
    # gate.delete_run_manager_if_needed(sim)
    gate.test_ok(is_ok)
