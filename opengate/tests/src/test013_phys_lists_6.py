#!/usr/bin/env python3
import opengate as gate
import os
from scipy.spatial.transform import Rotation


def start_simulation(phlist):
    # units
    km = gate.g4_units("km")
    cm = gate.g4_units("cm")
    mm = gate.g4_units("mm")
    MeV = gate.g4_units("MeV")

    # create the simulation
    sim = gate.Simulation()

    # add a material database
    sim.add_material_database(paths.gate_data / "HFMaterials2014.db")

    # main options
    ui = sim.user_info
    # ui.start_new_process = True
    ui.g4_verbose = False
    ui.g4_verbose_level = 2
    ui.visu = False
    ui.random_seed = "auto"  # 12365478910
    ui.random_engine = "MersenneTwister"

    # physics
    p = sim.get_physics_user_info()
    p.physics_list_name = phlist
    print()
    print("phys list = ", p.physics_list_name)
    p.enable_decay = False
    p.remove_radioactive_decay_physics = True
    sim.set_cut("world", "all", 1000 * km)

    #  change world size
    world = sim.world
    world.size = [600 * cm, 500 * cm, 500 * cm]

    # target
    phantom = sim.add_volume("Box", f"phantom_{phlist}")
    phantom.size = [200 * mm, 200 * mm, 200 * mm]
    phantom.translation = [-100 * mm, 0, 0]
    phantom.material = "G4_WATER"
    phantom.color = [0, 0, 1, 1]

    # dose actor
    dose = sim.add_actor("DoseActor", f"doseInXYZ_{phlist}")
    dose.output = output_path / f"edep_{phlist}.mhd"
    dose.mother = phantom.name
    dose.size = [200, 200, 200]
    dose.spacing = [1 * mm, 1 * mm, 1 * mm]
    dose.hit_type = "random"

    # source
    source = sim.add_source("GenericSource", "mysource")
    source.energy.mono = 1440 * MeV
    source.particle = "ion 6 12"
    source.position.type = "disc"
    source.position.rotation = Rotation.from_euler("y", 90, degrees=True).as_matrix()
    source.position.sigma_x = 8 * mm
    source.position.sigma_y = 8 * mm
    source.direction.type = "momentum"
    source.direction.momentum = [-1, 0, 0]
    source.n = 20

    # add stat actor
    s = sim.add_actor("SimulationStatisticsActor", "Stats")
    s.track_types_flag = True

    # start simulation
    sim = gate.SimulationEngine(sim, start_new_process=True)
    output = sim.start()

    # print results at the end
    stat = output.get_actor("Stats")
    print(stat)


# ------ INITIALIZE SIMULATION ENVIRONMENT ----------
paths = gate.get_default_test_paths(__file__, "gate_test044_pbs")
output_path = paths.output / "output_test051_rtp"

# create output dir, if it doesn't exist
if not os.path.isdir(output_path):
    os.mkdir(output_path)


physics_list_test = ["QGSP_BIC_HP", "QGSP_BIC"]
ref_phlist = physics_list_test[1]

for phlist in physics_list_test:
    start_simulation(phlist)

# ------ TESTS -------#
ref_filename = f"edep_{ref_phlist}.mhd"
ok = True

for phlist in physics_list_test:
    print()
    print(f"Checking {phlist=} vs {ref_phlist=}")
    ok = (
        gate.assert_images(
            output_path / ref_filename,
            output_path / f"edep_{phlist}.mhd",
            axis="x",
            tolerance=110,
            sum_tolerance=7,
        )
        and ok
    )

gate.test_ok(ok)
