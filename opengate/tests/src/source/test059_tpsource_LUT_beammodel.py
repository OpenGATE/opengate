import numpy as np
import opengate as gate
import gatetools
from opengate.tests import utility
from opengate.contrib.beamlines.ionbeamline import BeamlineModelLUT
from opengate.contrib.tps.ionbeamtherapy import SpotInfo


def root_load_key(data_ref, keys_ref, m_ref, key: str):
    index = keys_ref.index(key)
    values = [data_ref_i[index] for data_ref_i in data_ref]
    return values


def root_load_keys(data_ref, keys_ref, m_ref, keys: [str]):
    output = []
    for k in keys:
        output.append(root_load_key(data_ref, keys_ref, m_ref, k))
    return output


def find_outliers(v_data):
    v_data = np.array(v_data)
    mu = np.mean(v_data)
    std = np.std(v_data)
    is_outlier = (v_data > mu + 4 * std) | (v_data < mu - 4 * std)
    return is_outlier


def filter_outliers(v_data):
    mask = find_outliers(v_data)
    return np.array(v_data)[~mask]


if __name__ == "__main__":
    # ------ INITIALIZE SIMULATION ENVIRONMENT ----------
    paths = utility.get_default_test_paths(__file__, "gate_test044_pbs", "test059")
    output_path = paths.output
    ref_path = paths.output_ref

    # create the simulation
    sim = gate.Simulation()
    sim.output_dir = output_path

    # main options
    ui = sim.user_info
    ui.g4_verbose = False
    ui.g4_verbose_level = 1
    ui.visu = False
    ui.number_of_threads = 1
    # ui.random_seed = 12365478910c
    ui.random_engine = "MersenneTwister"

    # units
    m = gate.g4_units.m
    cm = gate.g4_units.cm
    mm = gate.g4_units.mm
    nm = gate.g4_units.nm
    rad = gate.g4_units.rad
    mrad = gate.g4_units.mrad
    MeV = gate.g4_units.MeV

    # add a material database
    sim.volume_manager.add_material_database(paths.data / "GateMaterials.db")

    #  change world size
    world = sim.world
    world.size = [500 * cm, 500 * cm, 500 * cm]
    world.material = "G4_AIR"

    # 2D air plane
    x_0 = sim.add_volume("Box", "phase_space_x_0")
    x_0.mother = sim.world
    x_0.material = "G4_AIR"
    x_0.size = [400 * mm, 400 * mm, 1 * nm]
    x_0.translation = [0, 0, 1 * nm]

    # physics
    sim.physics_manager.physics_list_name = "QGSP_BIC_HP_EMZ"

    sim.physics_manager.set_max_step_size(x_0.name, 1.0)
    sim.physics_manager.set_user_limits_particles("proton")
    # sim.physics_manager.user_limits_particles = ['proton','GenericIon']

    sim.physics_manager.set_production_cut("world", "gamma", 100 * m)
    sim.physics_manager.set_production_cut("world", "electron", 100 * m)
    sim.physics_manager.set_production_cut("world", "positron", 100 * m)

    # phase space actor
    phsp_x0 = sim.add_actor("PhaseSpaceActor", "PhaseSpace_x_0")
    phsp_x0.attached_to = x_0.name
    phsp_x0.attributes = [
        "KineticEnergy",
        "ParticleName",
        "PrePosition",
        "PreDirection",
    ]
    phsp_x0.output_filename = "PhSpace_x_0.root"
    f0 = sim.add_filter("ParticleFilter", "f0")
    f0.particle = "proton"
    phsp_x0.filters.append(f0)

    # beamline model
    beamline = BeamlineModelLUT()
    beamline.name = None
    beamline.radiation_types = "proton"
    beamline.distance_nozzle_iso = 0

    beamline.energy_mean_lut = [[100, 200], [100, 200]]
    beamline.energy_sigma_lut = [[100, 200], [0.1, 0.5]]
    beamline.sigma_x_lut = [[100, 200], [2 * mm, 4 * mm]]
    beamline.theta_x_lut = [[100, 200], [3 * mrad, 3 * mrad]]
    beamline.epsilon_x_lut = [[100, 200], [0.02 * mm * rad, 0.03 * mm * rad]]
    beamline.sigma_y_lut = [[100, 200], [2 * mm, 4 * mm]]
    beamline.theta_y_lut = [[100, 200], [3 * mrad, 3 * mrad]]
    beamline.epsilon_y_lut = [[100, 200], [0.02 * mm * rad, 0.03 * mm * rad]]
    beamline.MU_to_N_lut = [[100, 200], [1, 1]]
    beamline.conv_x = 0
    beamline.conv_y = 0

    # fak treatment plan with one spot, in (0,0), at 150 MeV
    energy = 150 * MeV
    beam_data = dict()
    spot1 = SpotInfo(0, 0, 1e3, energy)
    spot1.beamFraction = 1
    beam_data["n_fields"] = 1
    beam_data["plan_name"] = ""
    beam_data["msw_beam"] = 4e4
    beam_data["energies"] = [100, 200]
    beam_data["nb_spots"] = [1, 1]
    beam_data["spots"] = [spot1]
    beam_data["gantry_angle"] = 90
    beam_data["couch_angle"] = 0
    beam_data["isocenter"] = []

    # source
    tps = sim.add_source("TreatmentPlanPBSource", "TPSource")
    tps.n = 1e5
    tps.beam_model = beamline
    tps.beam_data_dict = beam_data
    tps.beam_nr = 1
    tps.gantry_rot_axis = "x"
    tps.particle = "proton"

    stat = sim.add_actor("SimulationStatisticsActor", "Stats")
    stat.track_types_flag = True
    sim.run(start_new_process=False)
    print(stat)

    # test:
    data_ref, keys_ref, m_ref = gatetools.phsp.load(phsp_x0.get_output_path_string())
    x_list_0, dir_x_list_0, y_list_0, dir_y_list_0, particle_name_0, energy_0 = (
        root_load_keys(
            data_ref,
            keys_ref,
            m_ref,
            [
                "PrePosition_X",
                "PreDirection_X",
                "PrePosition_Y",
                "PreDirection_Y",
                "ParticleName",
                "KineticEnergy",
            ],
        )
    )

    ok = True
    expected_E_mean = energy
    e_mean = np.mean(energy_0)
    ok = ok and np.isclose(e_mean, expected_E_mean, atol=1e-2)

    expected_E_sigma = gate.numerical.piecewise_linear_interpolation(
        energy, [100, 200], [0.1, 0.5]
    )
    e_sigma = np.std(filter_outliers(energy_0))
    ok = ok and np.isclose(e_sigma, expected_E_sigma, atol=1e-3)

    expected_beam_size = gate.numerical.piecewise_linear_interpolation(
        energy, [100, 200], [2 * mm, 4 * mm]
    )
    beam_size = np.std(filter_outliers(x_list_0))
    ok = ok and np.isclose(beam_size, expected_beam_size, atol=1e-2)

    expected_beam_divergence = gate.numerical.piecewise_linear_interpolation(
        energy, [100, 200], [3 * mrad, 3 * mrad]
    )
    beam_divergence = np.std(filter_outliers(dir_x_list_0))
    ok = ok and np.isclose(beam_divergence, expected_beam_divergence, atol=1e-2)

    utility.test_ok(ok)
