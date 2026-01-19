import logging

import opengate as gate
import opengate.contrib.linacs.electron_flash.electron_flash as fun
from opengate.tests import utility

# test_ElectronFlash_dose_app40.py


def create_electron_flash_simulation(paths, passive_collimation, fantom):
    # =====================================================
    # INITIALISATION
    # =====================================================

    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)

    mm = gate.g4_units.mm

    number_of_total_events = 5000

    sim = gate.Simulation()
    sim.verbose_level = gate.logger.RUN
    sim.running_verbose_level = gate.logger.RUN
    sim.g4_verbose = False
    sim.g4_verbose_level = 1
    sim.visu = False
    sim.visu_type = "qt"
    sim.random_engine = "MersenneTwister"
    sim.random_seed = 18101996
    sim.output_dir = paths.output
    sim.number_of_threads = 1
    sim.progress_bar = True
    if sim.visu:
        sim.number_of_threads = 1
        number_of_total_events = 1
    number_of_events = int(number_of_total_events / sim.number_of_threads) + 1

    sim.volume_manager.add_material_database(paths.data / "GateMaterials.db")

    # =====================================================
    # GEOMETRY
    # =====================================================

    ef_end = fun.build_ElectronFlash(sim, material_colors=fun.material_colors)
    if passive_collimation in ["app40", "app100"]:
        app_end = fun.build_passive_collimation(
            sim,
            passive_collimation,
            center_z=ef_end,
            material_colors=fun.material_colors,
        )
        dim_x, dim_y, dim_z = 250 * mm, 250 * mm, 60 * mm
    elif passive_collimation == "mb_40_slit_11":
        mb_end = fun.build_passive_collimation(
            sim, "app40", center_z=ef_end, material_colors=fun.material_colors
        )
        app_end = fun.build_passive_collimation(
            sim,
            passive_collimation,
            center_z=mb_end,
            material_colors=fun.material_colors,
        )
        dim_x, dim_y, dim_z = 100 * mm, 100 * mm, 20 * mm
    elif passive_collimation == "shaper40":
        shaper_end = fun.build_passive_collimation(
            sim, "app40", center_z=ef_end, material_colors=fun.material_colors
        )
        app_end, (leaf1, leaf2, leaf3, leaf4) = fun.build_passive_collimation(
            sim,
            passive_collimation,
            center_z=shaper_end,
            material_colors=fun.material_colors,
        )
        fun.set_shaper_aperture(
            leaf1, leaf2, leaf3, leaf4, aperture_x_mm=25, aperture_y_mm=35
        )
        fun.rotate_leaves_around_z(leaf1, leaf2, leaf3, leaf4, angle_deg=45)
        dim_x, dim_y, dim_z = 250 * mm, 250 * mm, 60 * mm
    elif passive_collimation == "nose":
        app_end = ef_end
    if fantom == "Phasespace_plane":
        dim_x, dim_y, dim_z = 150 * mm, 150 * mm, 0.01 * mm

    # =====================================================
    # PHANTOMS
    # =====================================================
    if fantom == "WaterBox":
        dosephantom = fun.build_dosephantombox(
            sim,
            "WaterBox",
            "Water",
            center_z=app_end + dim_z / 2,
            dimension_x=dim_x,
            dimension_y=dim_y,
            dimension_z=dim_z,
            material_colors=fun.material_colors,
        )

        dose = sim.add_actor("DoseActor", "dose")
        dose.attached_to = "WaterBox"
        dose.output_filename = "dose_test_" + passive_collimation + ".mhd"
        dose.hit_type = "random"
        dose.size = [120, 120, 30]  # Number of voxels
        dose.spacing = [1 * mm, 1 * mm, 2 * mm]  # Voxel size
        if passive_collimation == "mb_40_slit_11":
            dose.size = [250, 250, 20]  # Number of voxels
            dose.spacing = [0.1 * mm, 0.1 * mm, 1 * mm]  # Voxel size
        dose.dose.active = True
        dose.dose_uncertainty.active = False
        dose.edep_uncertainty.active = False
    elif fantom == "Phasespace_plane":
        phsp_plane = fun.build_dosephantombox(
            sim,
            "Phasespace_plane",
            "Air",
            center_z=app_end + dim_z / 2,
            dimension_x=dim_x,
            dimension_y=dim_y,
            dimension_z=dim_z,
            material_colors=fun.material_colors,
        )

        phsp = sim.add_actor("PhaseSpaceActor", "PhaseSpace")
        phsp.attached_to = phsp_plane.name
        phsp.attributes = [
            "KineticEnergy",
            "EventPosition",
        ]
        phsp.output_filename = "phsp_test_" + passive_collimation + ".root"

    # =====================================================
    # PHYSICS
    # =====================================================

    sim.physics_manager.physics_list_name = "G4EmStandardPhysics_option4"
    sim.physics_manager.set_production_cut("world", "all", 2 * mm)

    # =====================================================
    # SOURCE
    # =====================================================

    source = fun.add_source(sim, number_of_events)

    return sim


def analyze_dose(path_reference_dose, path_test_dose, tolerance=0.03):
    reference_pdd = fun.obtain_pdd_from_image(path_reference_dose)
    test_pdd = fun.obtain_pdd_from_image(path_test_dose)
    is_ok, mae = fun.evaluate_pdd_similarity(reference_pdd, test_pdd, tolerance)
    return (is_ok, mae)


def analyze_root(paths, path_reference_root_phsp, path_test_root_phsp):
    keys = [
        "KineticEnergy",
        "EventPosition_X",
        "EventPosition_Y",
    ]
    tols = [0.8, 0.8, 0.8]
    br = "PhaseSpace;1"
    name = "test_EF_" + str(path_reference_root_phsp).split("_")[-1] + ".png"
    is_ok = utility.compare_root3(
        path_reference_root_phsp,
        path_test_root_phsp,
        br,
        br,
        keys,
        keys,
        tols,
        None,
        None,
        paths.output / name,
        nb_bins=150,
        hits_tol=10**6,
    )
    return is_ok
