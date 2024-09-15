import opengate as gate

from scipy.spatial.transform import Rotation
import gatetools.phsp as phsp
import os
from opengate.tests import utility
from opengate.contrib.tps.treatmentPlanPhsSource import TreatmentPlanPhsSource
from opengate.contrib.tps.ionbeamtherapy import spots_info_from_txt
from pathlib import Path

# units
m = gate.g4_units.m
mm = gate.g4_units.mm
cm = gate.g4_units.cm
nm = gate.g4_units.nm
Bq = gate.g4_units.Bq
MeV = gate.g4_units.MeV
deg: float = gate.g4_units.deg


def create_test_phsp(
    particle="proton",
    phs_name=Path("output") / "test_proton.root",
    number_of_particles=1,
    translation=None,
):
    # create the simulation
    if translation is None:
        translation = [0 * mm, 0 * mm, 0 * mm]
    sim = gate.Simulation()

    # main options
    ui = sim.user_info
    ui.g4_verbose = False
    # ui.visu = True
    ui.visu_type = "vrml"
    ui.check_volumes_overlap = False
    # ui.running_verbose_level = gate.EVENT
    ui.number_of_threads = 1
    ui.random_seed = "auto"

    ##########################################################################################
    # geometry
    ##########################################################################################
    #  adapt world size
    world = sim.world
    world.size = [1 * m, 1 * m, 1 * m]
    world.material = "G4_Galactic"

    # virtual plane for phase space
    plane = sim.add_volume("Tubs", "phase_space_plane")
    # plane.material = "G4_AIR"
    plane.material = "G4_Galactic"
    plane.rmin = 0
    plane.rmax = 30 * cm
    plane.dz = 1 * nm  # half height
    # plane.rotation = Rotation.from_euler("xy", [180, 30], degrees=True).as_matrix()
    # plane.translation = [0 * mm, 0 * mm, 0 * mm]
    plane.translation = translation

    plane.color = [1, 0, 0, 1]  # red

    ##########################################################################################
    # Actors
    ##########################################################################################
    # Split the joined path into the directory path and filename
    directory_path, filename = os.path.split(phs_name)
    # Extract the base filename and extension
    base_filename, extension = os.path.splitext(filename)
    new_extension = ".root"

    # PhaseSpace Actor
    ta1 = sim.add_actor("PhaseSpaceActor", "PhaseSpace1")
    ta1.attached_to = plane
    ta1.attributes = [
        "KineticEnergy",
        "Weight",
        "PrePosition",
        "PrePositionLocal",
        "ParticleName",
        "PreDirection",
        "PreDirectionLocal",
        "PDGCode",
    ]
    new_joined_path = os.path.join(directory_path, base_filename + new_extension)
    ta1.output = new_joined_path
    ta1.debug = False
    f = sim.add_filter("ParticleFilter", "f")
    f.particle = particle
    ta1.filters.append(f)

    sim.physics_manager.physics_list_name = "QGSP_BIC_EMZ"

    ##########################################################################################
    #  Source
    ##########################################################################################
    source = sim.add_source("GenericSource", "particle_source")
    source.mother = "world"
    # source.particle = "ion 6 12"  # Carbon ions
    source.particle = "proton"
    source.position.type = "point"
    source.direction.type = "momentum"
    source.direction.momentum = [0, 0, 1]
    source.position.translation = [0 * cm, 0 * cm, -0.1 * cm]
    source.energy.type = "mono"
    source.energy.mono = 150 * MeV
    source.n = number_of_particles

    sim.run()
    output = sim.output


def create_phsp_without_source(
    output_dir=Path("output"),
    phs_name="test_proton.root",
):
    # create the simulation
    sim = gate.Simulation()

    # main options
    sim.g4_verbose = False
    # ui.visu = True
    sim.visu_type = "vrml"
    sim.check_volumes_overlap = False
    # ui.running_verbose_level = gate.EVENT
    sim.number_of_threads = 1
    sim.random_seed = "auto"
    sim.output_dir = output_dir

    ##########################################################################################
    # geometry
    ##########################################################################################
    #  adapt world size
    world = sim.world
    world.size = [1 * m, 1 * m, 1 * m]
    world.material = "G4_Galactic"
    print(world.name)

    # virtual plane for phase space
    plane = sim.add_volume("Tubs", "phase_space_plane")
    # plane.material = "G4_AIR"
    plane.material = "G4_Galactic"
    plane.rmin = 0
    plane.rmax = 30 * cm
    plane.dz = 1 * nm  # half height
    # plane.rotation = Rotation.from_euler("xy", [180, 30], degrees=True).as_matrix()
    plane.translation = [0 * mm, 0 * mm, 0 * mm]
    # plane.translation = translation

    plane.color = [1, 0, 0, 1]  # red

    ##########################################################################################
    # Actors
    ##########################################################################################

    # PhaseSpace Actor
    ta1 = sim.add_actor("PhaseSpaceActor", "PhaseSpace")
    ta1.attached_to = plane
    ta1.attributes = [
        "KineticEnergy",
        "Weight",
        "PrePosition",
        "PrePositionLocal",
        "ParticleName",
        "PreDirection",
        "PreDirectionLocal",
        "PDGCode",
    ]
    ta1.output_filename = phs_name
    ta1.debug = False

    sim.physics_manager.physics_list_name = "QGSP_BIC_EMZ"

    # ##########################################################################################
    # #  Source
    # ##########################################################################################
    # # phsp source
    # source = sim.add_source("PhaseSpaceSource", "phsp_source_global")
    # source.mother = world.name
    # source.phsp_file = source_name
    # source.position_key = "PrePosition"
    # source.direction_key = "PreDirection"
    # source.global_flag = True
    # source.particle = particle
    # source.batch_size = 3000
    # source.n = number_of_particles / ui.number_of_threads
    # # source.position.translation = [0 * cm, 0 * cm, -35 * cm]

    # output = sim.run()
    # output = sim.start()
    # output = sim.start(start_new_process=True)
    return sim, plane


def test_source_rotation_a(
    plan_file_name=Path("output") / "test_proton_offset.root",
    phs_list_file_name="PhsList.txt",
    phs_folder_name="",
    output_dir=Path("output"),
    phs_file_name_out="test_source_electron.root",
) -> gate.Simulation:
    sim, plane = create_phsp_without_source(
        phs_name=phs_file_name_out, output_dir=output_dir
    )
    number_of_particles = 1
    ##########################################################################################
    #  Source
    ##########################################################################################
    # TreatmentPlanPhsSource source
    tpPhSs = TreatmentPlanPhsSource("RT_plan", sim)
    tpPhSs.set_phaseSpaceList_file_name(phs_list_file_name)
    tpPhSs.set_phaseSpaceFolder(phs_folder_name)
    beam_dict = spots_info_from_txt(plan_file_name, "", 1)
    G = beam_dict["gantry_angle"]
    spots = beam_dict["spots"]
    tpPhSs.set_spots(spots)
    tpPhSs.set_particles_to_simulate(number_of_particles)
    tpPhSs.set_distance_source_to_isocenter(100 * cm)
    tpPhSs.set_distance_stearmag_to_isocenter(5 * m, 5 * m)
    tpPhSs.rotation = Rotation.from_euler("z", G, degrees=True)
    tpPhSs.initialize_tpPhssource()

    # depending on the rotation of the gantry, the rotation of the phase space to catch the particles is different
    plane.rotation = Rotation.from_euler("y", 90, degrees=True).as_matrix()

    sim.run()

    return sim


def get_first_entry_of_key(
    file_name_root=Path("output") / "test_source_electron.root", key="ParticleName"
):
    # read root file
    data_ref, keys_ref, m_ref = phsp.load(file_name_root)
    index = keys_ref.index(key)
    return data_ref[0][index]


def check_value_from_root_file(
    file_name_root=Path("output") / "test_source_electron.root",
    key="ParticleName",
    ref_value="e-",
):
    # read root file
    value = get_first_entry_of_key(file_name_root=file_name_root, key=key)
    if (type(ref_value) != str) and (type(value) != str):
        is_ok = utility.check_diff_abs(
            float(value), float(ref_value), tolerance=1e-3, txt=key
        )
    else:
        if value == ref_value:
            is_ok = True
        else:
            is_ok = False
    return is_ok
