#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
import opengate.contrib.phantoms.nemaiec as gate_iec
import opengate.sources.gansources as gansources
from opengate.sources.generic import get_rad_gamma_energy_spectrum
from opengate.contrib.spect import genm670
from scipy.spatial.transform import Rotation


def create_world(sim):
    # world size
    m = gate.g4_units.m
    sim.world.size = [1 * m, 1 * m, 1 * m]
    sim.world.material = "G4_AIR"


def set_phys(sim):
    m = gate.g4_units.m
    p = sim.get_physics_user_info()
    p.physics_list_name = "G4EmStandardPhysics_option3"
    sim.set_production_cut("world", "all", 1e3 * m)


def create_simu_with_genm670(sim, collimator_type="lehr", debug=False):
    # units
    mm = gate.g4_units.mm

    # world size
    create_world(sim)

    # spect system
    head1, crystal1 = genm670.add_ge_nm67_spect_head(
        sim, "spect1", collimator_type=collimator_type, debug=debug
    )
    head2, crystal2 = genm670.add_ge_nm67_spect_head(
        sim, "spect2", collimator_type=collimator_type, debug=debug
    )

    # default rotation to be in front of the IEC (not a realistic orientation)
    head1.translation = [0, 0, -280 * mm]
    head2.translation = [0, 0, 280 * mm]
    head1.rotation = Rotation.from_euler("y", 0, degrees=True).as_matrix()
    head2.rotation = Rotation.from_euler("y", 180, degrees=True).as_matrix()

    # digitizer
    keV = gate.g4_units.keV
    channels = [
        {"name": f"scatter", "min": 114 * keV, "max": 126 * keV},
        {"name": f"peak140", "min": 126 * keV, "max": 154 * keV},
    ]
    proj1 = genm670.add_digitizer(sim, crystal1.name, channels)
    proj2 = genm670.add_digitizer(sim, crystal2.name, channels)
    proj1.spacing = [3 * mm, 3 * mm]
    proj2.spacing = [3 * mm, 3 * mm]

    # stats
    sim.add_actor("SimulationStatisticsActor", "stats")

    # phys
    set_phys(sim)
    sim.set_production_cut("spect1", "all", 1 * mm)
    sim.set_production_cut("spect2", "all", 1 * mm)

    return proj1, proj2


def create_simu_with_gaga(
    sim, total_activity, activity_source, gaga_pth_filename, garf_pth_filename
):
    # world size
    create_world(sim)

    # add gaga source
    add_gaga_source(sim, total_activity, activity_source, gaga_pth_filename)

    # add arf plane
    mm = gate.g4_units.mm
    det1, det2 = add_garf_detector_planes(sim, head_radius=280 * mm)
    arf1, arf2 = add_garf_detectors(sim, garf_pth_filename, det1, det2)

    # stats
    sim.add_actor("SimulationStatisticsActor", "stats")

    # phys
    set_phys(sim)

    return arf1, arf2


def add_gaga_source(sim, total_activity, activity_source, gaga_pth_filename):
    mm = gate.g4_units.mm
    keV = gate.g4_units.keV
    gsource = sim.add_source("GANSource", "gaga")
    gsource.particle = "gamma"
    gsource.activity = total_activity
    gsource.pth_filename = gaga_pth_filename
    gsource.position_keys = ["PrePosition_X", "PrePosition_Y", "PrePosition_Z"]
    gsource.backward_distance = 50 * mm
    gsource.backward_force = True
    gsource.direction_keys = ["PreDirection_X", "PreDirection_Y", "PreDirection_Z"]
    gsource.energy_key = "KineticEnergy"
    gsource.energy_min_threshold = 10 * keV
    gsource.skip_policy = "ZeroEnergy"
    gsource.weight_key = None
    gsource.time_key = None
    gsource.batch_size = 5e4  # OSX
    # Linux 5e4 with 1 thread, 1e4 with 8 threads
    gsource.batch_size = 2e5 / sim.user_info.number_of_threads
    gsource.verbose_generator = False  # True
    gsource.gpu_mode = "auto"

    # conditional generator
    cond_generator = gansources.VoxelizedSourceConditionGenerator(
        activity_source, use_activity_origin=True
    )
    cond_generator.compute_directions = True
    gene = gansources.GANSourceConditionalGenerator(
        gsource, cond_generator.generate_condition
    )
    gsource.generator = gene


def add_garf_detector_planes(sim, head_radius):
    cm = gate.g4_units.cm
    nm = gate.g4_units.nm
    # GE colli size
    colli_size = [54.6 * cm, 40.6 * cm]  # FIXME function
    # colli_size = [100 * cm, 100 * cm]  # FIXME function
    colli_size = [128 * 3, 128 * 3]  # FIXME function
    pos, crystal_dist, psd = genm670.compute_plane_position_and_distance_to_crystal(
        "lehr"
    )
    print(pos, crystal_dist, psd)
    print(f"The detector plane position = {pos} mm")
    print(f"The detector head radius = {head_radius} mm")

    detector_plane1 = sim.add_volume("Box", "det_plane1")
    detector_plane1.material = "G4_Galactic"
    detector_plane1.color = [1, 0, 0, 1]
    detector_plane1.size = [colli_size[0], colli_size[1], 1 * nm]
    r = Rotation.from_euler("x", 0, degrees=True)
    detector_plane1.rotation = r.as_matrix()
    detector_plane1.translation = [0, 0, -head_radius - pos]
    print(f"{detector_plane1.translation=}")

    detector_plane2 = sim.add_volume("Box", "det_plane2")
    detector_plane2.material = "G4_Galactic"
    detector_plane2.color = [1, 0, 0, 1]
    detector_plane2.size = [colli_size[0], colli_size[1], 1 * nm]
    r = Rotation.from_euler("y", 180, degrees=True)
    detector_plane2.rotation = r.as_matrix()
    detector_plane2.translation = [0, 0, -head_radius - pos]
    detector_plane2.translation = r.apply(detector_plane2.translation)
    print(f"{detector_plane2.translation=}")
    # FIXME apply rotation to translation

    return detector_plane1, detector_plane2


def add_garf_detectors(sim, pth_filename, det1, det2):
    mm = gate.g4_units.mm
    detectors = [det1, det2]

    pos, crystal_dist, psd = genm670.compute_plane_position_and_distance_to_crystal(
        "lehr"
    )
    print(f"{pos=}")
    print(f"{crystal_dist=}")
    print(f"{psd=}")

    arfs = []
    for det in detectors:
        # arf actor
        arf = sim.add_actor("ARFActor", f"arf_{det.name}")
        arf.mother = det.name
        arf.batch_size = 1e5
        arf.image_size = [128, 128]
        arf.image_spacing = [3 * mm, 3 * mm]
        arf.verbose_batch = True
        arf.distance_to_crystal = crystal_dist
        arf.gpu_mode = "auto"
        arf.pth_filename = pth_filename
        arf.enable_hit_slice = False
        arfs.append(arf)

    return arfs[0], arfs[1]


def set_duration(sim, total_activity, w, duration):
    Bq = gate.g4_units.Bq
    sec = gate.g4_units.second
    ui = sim.user_info
    nb_decays = total_activity / Bq * duration / sec * ui.number_of_threads
    weights = sum(w)
    print(f"Estimated total decay {nb_decays:.0f} decays")
    print(
        f"Estimated gammas {nb_decays * weights:.0f} gammas (weights = {weights:.4f})"
    )
    sim.run_timing_intervals = [[0, duration]]


def add_iec_Tc99m_source(sim, activity_concentration):
    cm3 = gate.g4_units.cm3
    Bq = gate.g4_units.Bq
    kBq = 1000 * Bq
    MBq = 1000 * kBq
    BqmL = Bq / cm3
    ui = sim.user_info

    # same concentration in all spheres
    a = activity_concentration / ui.number_of_threads
    all_activities = [a] * 6

    # Tc99m
    sources = gate_iec.add_spheres_sources(sim, "iec", "src", "all", all_activities)
    total_activity = 0
    print(f"Activity concentration = {all_activities[5] / BqmL:.0f} BqmL")
    w, e = get_rad_gamma_energy_spectrum("Tc99m")
    for source in sources:
        source.particle = "gamma"
        source.energy.type = "spectrum_lines"
        source.energy.spectrum_weight = w
        source.energy.spectrum_energy = e
        total_activity += source.activity
        print(
            f"Activity {source.name} = {source.activity / Bq:.2f} Bq  {activity_concentration / BqmL:.0f} Bq/mL"
        )

    print(f"Total activity 1 thread = {total_activity / Bq:.2f} Bq")
    print(f"Total activity 1 thread = {total_activity / kBq:.2f} kBq")
    print(f"Total activity 1 thread = {total_activity / MBq:.2f} MBq")
    print(
        f"Total activity {ui.number_of_threads} threads = {total_activity / MBq * ui.number_of_threads:.2f} MBq"
    )

    return total_activity, w, e
