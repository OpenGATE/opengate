#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from scipy.spatial.transform import Rotation
import opengate as gate
from opengate.tests import utility


def run_test_re(particle="carbon"):

    paths = utility.get_default_test_paths(__file__, "test_087")
    print(paths)
    ref_path = paths.output_ref / "test087"
    # create the simulation
    sim = gate.Simulation()

    # main options
    ui = sim.user_info
    ui.g4_verbose = False
    ui.g4_verbose_level = 1
    ui.visu = False
    ui.random_seed = 12345678910
    ui.number_of_threads = 1
    if particle == "proton":
        numPartSimTest = 5e2 / ui.number_of_threads
    else:
        numPartSimTest = 4000 / ui.number_of_threads

    # units
    m = gate.g4_units.m
    cm = gate.g4_units.cm
    mm = gate.g4_units.mm
    km = gate.g4_units.km
    MeV = gate.g4_units.MeV
    Bq = gate.g4_units.Bq
    kBq = 1000 * Bq

    #  change world size
    world = sim.world
    world.size = [600 * cm, 500 * cm, 500 * cm]
    # world.material = "Vacuum"

    # waterbox
    phantom = sim.add_volume("Box", "phantom")
    phantom.size = [10 * cm, 10 * cm, 10 * cm]
    phantom.translation = [-5 * cm, 0, 0]
    phantom.material = "G4_WATER"
    phantom.color = [0, 0, 1, 1]

    test_material_name = "G4_WATER"
    phantom_off = sim.add_volume("Box", "phantom_off")
    phantom_off.mother = phantom.name
    phantom_off.size = [100 * mm, 60 * mm, 60 * mm]
    phantom_off.translation = [0 * mm, 0 * mm, 0 * mm]
    phantom_off.material = test_material_name
    phantom_off.color = [0, 0, 1, 1]

    # physics
    sim.physics_manager.physics_list_name = "FTFP_INCLXX_HP_EMZ"

    # default source for tests
    source = sim.add_source("GenericSource", "mysource")
    if particle == "proton":
        source.energy.mono = 80 * MeV
        source.particle = "proton"
    else:
        source.energy.mono = 1424 * MeV
        source.particle = "ion 6 12"

    source.position.type = "disc"
    source.position.rotation = Rotation.from_euler("y", 90, degrees=True).as_matrix()
    source.position.radius = 4 * mm
    source.position.translation = [0, 0, 0]
    source.direction.type = "momentum"
    source.direction.momentum = [-1, 0, 0]
    # print(dir(source.energy))
    source.n = numPartSimTest
    # source.activity = 100 * kBq

    size = [50, 1, 1]
    spacing = [2.0 * mm, 60.0 * mm, 60.0 * mm]

    doseActorName_IDD_d = f"IDD_d_{particle}"
    doseIDD = sim.add_actor("DoseActor", doseActorName_IDD_d)
    doseIDD.output_filename = paths.output / ("test087-" + doseActorName_IDD_d + ".mhd")
    #    print(f'actor: {paths.output / ("test087-" + doseActorName_IDD_d + ".mhd")}')
    doseIDD.attached_to = phantom_off.name
    doseIDD.size = size
    doseIDD.spacing = spacing
    doseIDD.hit_type = "random"
    doseIDD.dose.active = False

    RE = f"RE_{particle}"
    RE_act = sim.add_actor("REActor", RE)
    RE_act.output_filename = paths.output / ("test087-" + RE + ".mhd")
    RE_act.attached_to = phantom_off.name
    RE_act.size = size
    RE_act.spacing = spacing
    RE_act.hit_type = "random"
    RE_act.model = "RE"
    # TODO: note that EMCalculator throws a segfault for O16 at low energies for G4_Alanine; therfore we cannot use it although we should
    #    RE_act.score_in = "G4_ALANINE"
    RE_act.score_in = "G4_WATER"
    RE_act.lookup_table_path = ref_path / "RE_Alanine_RBEstyle.txt"

    # add stat actor
    s = sim.add_actor("SimulationStatisticsActor", "stats")
    s.track_types_flag = True

    sim.run(start_new_process=True)

    # ----------------------------------------------------------------------------------------------------------------

    if particle == "proton":
        ref_fpath = (
            ref_path
            / "test087_REalanine__Proton_Energy80spread1MeV_PrimaryProton-relEfficiency-letToG4_ALANINE.mhd"
        )
    else:
        ref_fpath = (
            ref_path
            / "test087_REalanine__Carbon_Energy1424spread1MeV_PrimaryCarbon-relEfficiency-letToG4_ALANINE.mhd"
        )
    print(f"{doseIDD.dose.get_output_path()=}")
    is_ok = utility.assert_filtered_imagesprofile1D(
        ref_filter_filename1=doseIDD.edep.get_output_path(),
        ref_filename1=ref_fpath,
        filename2=paths.output / RE_act.RE_mix.get_output_path(),
        tolerance=20,
        #        plt_ylim=[0, 2],
        eval_quantity="RE",
    )
    return is_ok


def main():
    print("Running proton test case for relative effectiveness")
    is_ok = run_test_re("proton")
    print("... continue with carbon ion beam")
    is_ok = is_ok and run_test_re("carbon")
    utility.test_ok(is_ok)


if __name__ == "__main__":
    main()
