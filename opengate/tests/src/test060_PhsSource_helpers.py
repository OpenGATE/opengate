import opengate as gate
from scipy.spatial.transform import Rotation
import gatetools.phsp as phsp
import os

# units
m = gate.g4_units("m")
mm = gate.g4_units("mm")
cm = gate.g4_units("cm")
nm = gate.g4_units("nm")
Bq = gate.g4_units("Bq")
MeV = gate.g4_units("MeV")
deg: float = gate.g4_units("deg")


def create_test_Phs(
    particle="proton",
    phs_name="output/test_proton.root",
    number_of_particles=1,
    translation=[0 * mm, 0 * mm, 0 * mm],
):
    # create the simulation
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

    # units
    m = gate.g4_units("m")
    cm = gate.g4_units("cm")
    nm = gate.g4_units("nm")
    MeV = gate.g4_units("MeV")

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
    ta1.mother = plane.name
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

    # PhaseSpace Actor
    ta2 = sim.add_actor("PhaseSpaceActor", "PhaseSpace2")
    ta2.mother = plane.name
    ta2.attributes = [
        "KineticEnergy",
        "Weight",
        "PrePosition",
        "PrePositionLocal",
        "PreDirection",
        "PreDirectionLocal",
    ]
    new_joined_path = os.path.join(
        directory_path, base_filename + "_noParticleInfo" + new_extension
    )
    ta2.output = new_joined_path
    ta2.debug = False
    ta2.filters.append(f)

    # PhaseSpace Actor
    ta3 = sim.add_actor("PhaseSpaceActor", "PhaseSpace3")
    ta3.mother = plane.name
    ta3.attributes = [
        "KineticEnergy",
        "Weight",
        "PrePosition",
        "PrePositionLocal",
        "PreDirection",
        "PreDirectionLocal",
        "PDGCode",
    ]
    new_joined_path = os.path.join(
        directory_path, base_filename + "_PDGCode" + new_extension
    )
    ta3.output = new_joined_path
    ta3.debug = False
    ta3.filters.append(f)

    # PhaseSpace Actor
    ta4 = sim.add_actor("PhaseSpaceActor", "PhaseSpace4")
    ta4.mother = plane.name
    ta4.attributes = [
        "KineticEnergy",
        "Weight",
        "PrePosition",
        "PrePositionLocal",
        "PreDirection",
        "PreDirectionLocal",
        "ParticleName",
    ]
    new_joined_path = os.path.join(
        directory_path, base_filename + "_ParticleName" + new_extension
    )
    ta4.output = new_joined_path
    ta4.debug = False
    ta4.filters.append(f)

    # ~ sim.physics_manager.physics_list_name = "FTFP_BERT"
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

    sim.run(start_new_process=True)


def create_PhS_withoutSource(
    phs_name="output/test_proton.root",
):
    # create the simulation
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

    # units
    m = gate.g4_units("m")
    mm = gate.g4_units("mm")
    cm = gate.g4_units("cm")
    nm = gate.g4_units("nm")

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
    ta1.mother = plane.name
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
    ta1.output = phs_name
    ta1.debug = True

    # ~ phys.physics_list_name = "FTFP_BERT"
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
    return sim


def test_source_name(
    source_file_name="output/test_proton_offset.root",
    phs_file_name_out="output/output/test_source_electron.root",
) -> None:
    sim = create_PhS_withoutSource(
        phs_name=phs_file_name_out,
    )
    particle = "e-"
    number_of_particles = 1
    ##########################################################################################
    #  Source
    ##########################################################################################
    # phsp source
    source = sim.add_source("PhaseSpaceSource", "phsp_source_global")
    source.mother = "world"
    source.phsp_file = source_file_name
    source.position_key = "PrePositionLocal"
    source.direction_key = "PreDirectionLocal"
    source.global_flag = True
    source.particle = particle
    source.batch_size = 3000
    source.n = number_of_particles
    # source.position.translation = [0 * cm, 0 * cm, -35 * cm]

    sim.run()


def test_source_particleInfo_from_Phs(
    source_file_name="output/test_proton_offset.root",
    phs_file_name_out="output/test_source_PDG_proton.root",
) -> None:
    sim = create_PhS_withoutSource(
        phs_name=phs_file_name_out,
    )
    number_of_particles = 1
    ##########################################################################################
    #  Source
    ##########################################################################################
    # phsp source
    source = sim.add_source("PhaseSpaceSource", "phsp_source_global")
    source.mother = "world"
    source.phsp_file = source_file_name
    source.particle = ""
    source.position_key = "PrePositionLocal"
    source.direction_key = "PreDirectionLocal"
    source.global_flag = True
    source.batch_size = 3000
    source.n = number_of_particles
    # source.position.translation = [0 * cm, 0 * cm, -35 * cm]

    sim.run()


def test_source_translation(
    source_file_name="output/test_proton_offset.root",
    phs_file_name_out="output/output/test_source_electron.root",
) -> None:
    sim = create_PhS_withoutSource(
        phs_name=phs_file_name_out,
    )
    number_of_particles = 1
    ##########################################################################################
    #  Source
    ##########################################################################################
    # phsp source
    source = sim.add_source("PhaseSpaceSource", "phsp_source_global")
    source.mother = "world"
    source.phsp_file = source_file_name
    source.position_key = "PrePosition"
    source.direction_key = "PreDirection"
    source.global_flag = True
    source.particle = "proton"
    source.batch_size = 3000
    source.n = number_of_particles
    source.override_position = True
    source.position.translation = [3 * cm, 0 * cm, 0 * cm]
    print(source)

    sim.run()


def test_source_rotation(
    source_file_name="output/test_proton_offset.root",
    phs_file_name_out="output/output/test_source_electron.root",
) -> None:
    sim = create_PhS_withoutSource(
        phs_name=phs_file_name_out,
    )
    number_of_particles = 1
    ##########################################################################################
    #  Source
    ##########################################################################################
    # phsp source
    source = sim.add_source("PhaseSpaceSource", "phsp_source_global")
    source.mother = "world"
    source.phsp_file = source_file_name
    source.position_key = "PrePosition"
    source.direction_key = "PreDirection"
    source.global_flag = True
    source.particle = "proton"
    source.batch_size = 3000
    source.n = number_of_particles
    # source.override_position = True
    # source.position.translation = [3 * cm, 1 * cm, 0 * cm]
    source.override_direction = True
    # rotation = Rotation.from_euler("zyx", [30, 20, 10], degrees=True)
    rotation = Rotation.from_euler("x", [30], degrees=True)
    source.position.rotation = rotation.as_matrix()
    print(source)

    sim.run()


def get_first_entry_of_key(
    file_name_root="output/test_source_electron.root", key="ParticleName"
) -> None:
    # read root file
    data_ref, keys_ref, m_ref = phsp.load(file_name_root)
    # print(data_ref)
    # print(keys_ref)
    index = keys_ref.index(key)
    # print(index)
    # print(data_ref[index][0])
    return data_ref[0][index]


def check_value_from_root_file(
    file_name_root="output/test_source_electron.root",
    key="ParticleName",
    ref_value="e-",
):
    # read root file
    value = get_first_entry_of_key(file_name_root=file_name_root, key=key)
    if (type(ref_value) != str) and (type(value) != str):
        is_ok = gate.check_diff_abs(
            float(value), float(ref_value), tolerance=1e-6, txt=key
        )
    # gate.check_diff_abs(float(value), float(ref_value), tolerance=1e-6, txt=key)
    else:
        if value == ref_value:
            # print("Is correct")
            is_ok = True
        else:
            # print("Is not correct")
            is_ok = False
    # print("ref_value: ", ref_value)
    # print("value: ", value)
    return is_ok
