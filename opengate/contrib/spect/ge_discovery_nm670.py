import pathlib
from opengate.managers import Simulation
from opengate.geometry.volumes import (
    RepeatParametrisedVolume,
    HexagonVolume,
    unite_volumes,
)
from opengate.geometry.utility import (
    get_transform_orbiting,
)
from opengate.actors.digitizers import *
from opengate.contrib.spect.spect_helpers import (
    get_volume_bounding_box_coordinate_in_frame,
    get_default_energy_windows,
)
from scipy.spatial.transform import Rotation
from box import Box
import json


def get_geometrical_parameters_filename():
    filename = (
        pathlib.Path(__file__).parent / "ge_discovery_nm670_geometrical_parameters.json"
    )
    return pathlib.Path(filename)


geometrical_parameters = None


def get_geometrical_parameters():
    global geometrical_parameters
    if geometrical_parameters is None:
        filename = get_geometrical_parameters_filename()
        if not filename.exists():
            print(f'update geometrical parameters to "{filename}"')
            update_geometrical_parameters(store_to_file=True)
        # print(f'Loading geometrical parameters from "{filename}"')
        with open(filename) as json_file:
            geometrical_parameters = json.load(json_file)
        geometrical_parameters = Box(geometrical_parameters)
    return geometrical_parameters


def update_geometrical_parameters(store_to_file=False):
    p = Box()
    p.collimators = ["lehr", "megp", "hegp"]
    # for all colli
    nm = g4_units.nm
    for c in p.collimators:
        s = Simulation()
        spect, colli, crystal = add_spect_head(s, "spect", c, debug=True)
        pos = get_volume_bounding_box_coordinate_in_frame(
            s, "spect", f"collimator_trd", "max", axis=2
        )
        y = get_volume_bounding_box_coordinate_in_frame(
            s, "spect", "crystal", "center", axis=2
        )
        psd = get_volume_bounding_box_coordinate_in_frame(
            s, "spect", "collimator_psd", "min", axis=2
        )
        p[c] = Box()
        # distance from box boundary to collimator
        p[c].collimator_position = pos
        # distance to the center of the box head
        p[c].half_box_size = spect.size[2] / 2.0 + 1 * nm
        # distance from box boundary to crystal center (for arf)
        p[c].crystal_distance = p[c].half_box_size - y
        # distance from box boundary to the collimator_psd
        p[c].psd = p[c].half_box_size - psd

        # collimator holes
        hole = s.volume_manager.get_volume(f"spect_collimator_hole")
        p[c].hole_diameter = hole.radius * 2
        p[c].collimator_length = hole.height
        holep = s.volume_manager.get_volume(f"spect_collimator_hole_param")
        tr = holep.translation
        p[c].septa_thickness = tr[1] - p[c].hole_diameter

    if store_to_file:
        filename = get_geometrical_parameters_filename()
        with open(filename, "w") as json_file:
            json.dump(p, json_file, indent=4)

    return p


def get_collimator(rad):
    radionuclides = ["tc99m", "lu177", "in111", "i131"]
    ref_collimators = ["lehr", "megp", "megp", "hegp"]
    rad = rad.lower()
    if rad not in radionuclides:
        fatal(f'The radionuclide "{rad}" is unknown. Known are: {radionuclides}')
    return ref_collimators[radionuclides.index(rad)]


def add_fake_spect_head(sim, name="spect"):
    white = [1, 1, 1, 1]
    cm = g4_units.cm
    spect_length = 19 * cm
    head = sim.add_volume("Box", name)
    head.material = "G4_AIR"
    head.size = [57.6 * cm, 44.6 * cm, spect_length]
    head.color = white
    return head


def get_orientation_for_ct(colli_type, table_shift, radius):
    nm = g4_units.nm
    pos, crystal_distance, psdd = get_plane_position_and_distance_to_crystal_OLD(
        colli_type
    )
    pos += 1 * nm
    p = [0, table_shift, -(radius + psdd)]
    return get_transform_orbiting(p, "x", 90)


def add_materials(sim):
    f = pathlib.Path(__file__).parent.resolve()
    fdb = f"{f}/spect_ge_nm670_materials.db"
    if fdb not in sim.volume_manager.material_database.filenames:
        sim.volume_manager.add_material_database(fdb)


def add_spect_head(
    sim,
    name="spect",
    collimator_type="lehr",
    rotation_deg=0,
    debug=False,
    crystal_size="3/8",
):
    """
    Collimators:
    - False : no collimator
    - lehr : holes length 35 mm, diam 1.5 mm, septal thickness : 0.2 mm
    - megp : holes length 58 mm, diam 3 mm,   septal thickness : 1.05 mm
    - hegp : holes length 66 mm, diam 4 mm,   septal thickness : 1.8 mm

    Collimator LEHR: Low Energy High Resolution    (for Tc99m)
    Collimator MEGP: Medium Energy General Purpose (for In111, Lu177)
    Collimator HEGP: High Energy General Purpose   (for I131)

    """
    add_materials(sim)

    # check overlap
    # sim.check_volumes_overlap = False # set to True for debug

    # spect head
    head, lead_cover = add_spect_box(sim, name, crystal_size)

    # spect head
    crystal = add_crystal(sim, name, lead_cover, crystal_size)

    # spect collimator
    colli = None
    if collimator_type:
        colli = add_collimator(sim, name, head, collimator_type, rotation_deg, debug)

    # default orientation
    set_default_orientation(head, collimator_type)

    return head, colli, crystal


def set_default_orientation(head, collimator_type):
    # default head translation to set the shielding_front at position 0
    # (this translation is considered in rotate_gantry)
    p = get_geometrical_parameters()
    if collimator_type:
        tr = p[collimator_type].half_box_size - p[collimator_type].psd
    else:
        tr = 0
    head.translation = [0, tr, 0]

    # also the orientation is set such as Y is the normal of the detector
    rot = Rotation.from_euler("xy", (90, 0), degrees=True)
    head.rotation = rot.as_matrix()


def add_spect_two_heads(
    sim, name="spect", collimator_type="lehr", debug=False, radius=None
):
    cm = g4_units.cm
    if radius is None:
        radius = 36 * cm
    head1, colli1, crystal1 = add_spect_head(
        sim, f"{name}_1", collimator_type, debug=debug
    )

    # the second head is the same at 180 degrees
    head2, colli2, crystal2 = add_spect_head(
        sim, f"{name}_2", collimator_type, debug=debug
    )

    # set at their initial position
    set_default_orientation(head1, collimator_type)
    rotate_gantry(head1, radius, start_angle_deg=0, step_angle_deg=1, nb_angle=1)
    set_default_orientation(head2, collimator_type)
    rotate_gantry(head2, radius, start_angle_deg=180, step_angle_deg=1, nb_angle=1)

    return [head1, head2], [crystal1, crystal2]


def distance_to_center_of_crystal(sim, name="spect"):
    lead_cover = sim.volume_manager.volumes[f"{name}_lead_cover"]
    crystal = sim.volume_manager.volumes[f"{name}_crystal"]
    # distance from center to center of crystal
    shielding = sim.volume_manager.volumes[f"{name}_shielding"]
    d = shielding.translation[2] + lead_cover.translation[2] + crystal.translation[2]
    return d


def add_spect_box(sim, name, crystal_size):
    cm = g4_units.cm

    # colors
    blue = [0.5, 0.5, 1, 0.8]
    gray = [0.5, 0.5, 0.5, 1]
    white = [1, 1, 1, 1]
    yellow = [1, 1, 0, 1]
    green = [0, 1, 0, 1]

    # the total length
    spect_length = 19 * cm

    # bounding box
    head = sim.add_volume("Box", name)
    head.material = "G4_AIR"
    head.size = [57.6 * cm, 44.6 * cm, spect_length]
    head.color = white

    # shielding
    shielding = sim.add_volume("Box", f"{name}_shielding")
    shielding.mother = head.name
    shielding.size = head.size.copy()
    shielding.size[2] = 11.1375 * cm
    shielding.translation = [0, 0, -3.64 * cm]
    shielding.material = "Steel"
    shielding.color = yellow

    # shielding lead cover
    lead_cover = sim.add_volume("Box", f"{name}_lead_cover")
    lead_cover.mother = shielding.name
    lead_cover.size = [57.6 * cm, 40.6 * cm, 10.1375 * cm]
    lead_cover.translation = [0, 0, 0.5 * cm]
    lead_cover.material = "Lead"
    lead_cover.color = gray

    # crystal size
    if crystal_size == "3/8":
        cs = 0.9525 * cm
    else:
        cs = 1.5875 * cm

    # shielding alu cover
    alu_cover = sim.add_volume("Box", f"{name}_alu_cover")
    alu_cover.mother = lead_cover.name
    alu_cover.size = [54 * cm, 40 * cm, 0.13 * cm]
    alu_cover.translation = [0, 0, 5.00375 * cm]
    alu_cover.material = "Aluminium"
    alu_cover.color = blue

    # shielding reflector
    reflector = sim.add_volume("Box", f"{name}_reflector")
    reflector.mother = lead_cover.name
    reflector.size = [54 * cm, 40 * cm, 0.12 * cm]
    # reflector.translation = [0, 0, 3.92625 * cm] # for 3/8
    reflector.translation[2] = (
        lead_cover.size[2] / 2 - alu_cover.size[2] - cs - reflector.size[2] / 2
    )
    reflector.material = "TiO2"
    reflector.color = green

    # backside
    # The back-side is fairly complex, and may have a strong influence on the
    # spectrum: the model shown here is simplified
    backside = sim.add_volume("Box", f"{name}_backside")
    backside.mother = lead_cover.name
    h = alu_cover.size[2] + cs + reflector.size[2]
    backside.size = [54 * cm, 40 * cm, 8 * cm]
    # backside.translation = [0, 0, -0.13375 * cm] # for 3/8
    t = lead_cover.size[2] / 2 - h - backside.size[2] / 2
    backside.translation[2] = t
    backside.material = "Pyrex66"
    backside.color = blue

    return head, lead_cover


def add_crystal(sim, name, lead_cover, crystal_size):
    cm = g4_units.cm
    yellow = [1, 1, 0, 1]
    alu_cover_z = 0.13 * cm
    ref_z = 0.12 * cm
    # mono-bloc crystal thickness 3/8 of inch = 0.9525 cm
    # (if 5/8 inch = 1.5875 ; but probably need to translate elements)
    crystal = sim.add_volume("Box", f"{name}_crystal")
    crystal.mother = lead_cover.name
    if crystal_size == "3/8":
        crystal.size = [54 * cm, 40 * cm, 0.9525 * cm]
    else:
        crystal.size = [54 * cm, 40 * cm, 1.5875 * cm]
    crystal.translation[2] = lead_cover.size[2] / 2 - crystal.size[2] / 2 - alu_cover_z
    crystal.material = "NaITl"
    crystal.color = yellow
    return crystal


def add_collimator(sim, name, head, collimator_type, rotation_deg, debug):
    """
    Start with default lehr collimator description,
    then change some parameters for the other types
    """
    cm = g4_units.cm

    # colors
    red = [1, 0.7, 0.7, 0.8]
    blue = [0.5, 0.5, 1, 0.8]
    green = [0, 1, 0, 1]

    # mono-bloc crystal thickness 3/8 of inch
    colli_trd = sim.add_volume("Trd", f"{name}_collimator_trd")
    colli_trd.mother = head.name
    colli_trd.dx2 = 56.8 * cm / 2.0
    colli_trd.dy2 = 42.8 * cm / 2.0
    colli_trd.dx1 = 57.6 * cm / 2.0
    colli_trd.dy1 = 44.6 * cm / 2.0
    colli_trd.dz = 4.18 * cm / 2.0  # dep. on colli type
    colli_trd.translation = [0, 0, 4.02 * cm]  # dep. on colli type
    colli_trd.material = "G4_AIR"
    colli_trd.color = red

    # PSD (Position Sensitive Detection)
    psd = sim.add_volume("Box", f"{name}_collimator_psd")
    psd.mother = colli_trd.name
    psd.size = [54.6 * cm, 40.6 * cm, 0.1 * cm]
    psd.translation = [0, 0, 2.04 * cm]  # dep. on colli type
    psd.material = "Aluminium"
    psd.color = green

    # PSD layer
    psd_layer = sim.add_volume("Box", f"{name}_collimator_psd_layer")
    psd_layer.mother = colli_trd.name
    psd_layer.size = [54.6 * cm, 40.6 * cm, 0.15 * cm]
    psd_layer.translation = [0, 0, 1.915 * cm]  # dep. on colli type
    psd_layer.material = "PVC"
    psd_layer.color = red

    # Alu cover
    alu_cover = sim.add_volume("Box", f"{name}_collimator_alu_cover")
    alu_cover.mother = colli_trd.name
    alu_cover.size = [54.6 * cm, 40.6 * cm, 0.05 * cm]
    alu_cover.translation = [0, 0, -2.065 * cm]  # dep. on colli type
    alu_cover.material = "Aluminium"
    alu_cover.color = blue

    # air gap
    air_gap = sim.add_volume("Box", f"{name}_collimator_air_gap")
    air_gap.mother = colli_trd.name
    air_gap.size = [54.6 * cm, 40.6 * cm, 0.38 * cm]
    air_gap.translation = [0, 0, 1.65 * cm]  # dep. on colli type
    air_gap.material = "G4_AIR"
    air_gap.color = blue

    # core
    core = sim.add_volume("Box", f"{name}_collimator_core")
    core.mother = colli_trd.name
    core.size = [54.6 * cm, 40.6 * cm, 3.5 * cm]  # dep. on colli type
    core.translation = [0, 0, -0.29 * cm]
    core.material = "Lead"
    core.color = blue

    # adapt according to collimator type
    if collimator_type == "megp":
        colli_trd.dz = 6.48 * cm / 2.0
        colli_trd.translation = [0, 0, 5.17 * cm]
        psd.translation = [0, 0, 3.19 * cm]
        psd_layer.translation = [0, 0, 3.065 * cm]
        alu_cover.translation = [0, 0, -3.215 * cm]
        air_gap.translation = [0, 0, 2.80 * cm]
        core.size = [54.6 * cm, 40.6 * cm, 5.8 * cm]

    if collimator_type == "hegp":
        colli_trd.dz = 7.28 * cm / 2.0
        colli_trd.translation = [0, 0, 5.57 * cm]
        psd.translation = [0, 0, 3.59 * cm]
        psd_layer.translation = [0, 0, 3.465 * cm]
        alu_cover.translation = [0, 0, -3.615 * cm]
        air_gap.translation = [0, 0, 3.2 * cm]
        core.size = [54.6 * cm, 40.6 * cm, 6.6 * cm]

    # repeater for the holes
    holep = None
    if collimator_type == "megp":
        holep = megp_collimator_repeater(sim, name, core, debug)
    if collimator_type == "lehr":
        holep = lehr_collimator_repeater(sim, name, core, debug)
    if collimator_type == "hegp":
        holep = hegp_collimator_repeater(sim, name, core, debug)
    if not holep:
        fatal(
            f"Error, unknown collimator type {collimator_type}. "
            f'Use "megp" or "lehr" or "hegp" or "False"'
        )

    # should we rotate the collimator holes ?
    holep.rotation = Rotation.from_euler("Z", rotation_deg, degrees=True).as_matrix()

    return colli_trd


def hegp_collimator_repeater(sim, name, core, debug):
    cm = g4_units.cm
    mm = g4_units.mm
    # one single hole
    hole = sim.add_volume("Hexagon", f"{name}_collimator_hole")
    hole.height = 6.6 * cm
    hole.radius = 0.2 * cm
    hole.material = "G4_AIR"
    hole.mother = core.name

    # parameterised holes
    holep = RepeatParametrisedVolume(repeated_volume=hole)
    holep.linear_repeat = [54, 70, 1]
    if debug:
        holep.linear_repeat = [10, 10, 1]
    holep.translation = [10.0459 * mm, 5.8 * mm, 0]
    # dot it twice, with the following offset
    holep.offset_nb = 2
    holep.offset = [5.0229 * mm, 2.9000 * mm, 0]

    sim.volume_manager.add_volume(holep)
    return holep


def megp_collimator_repeater(sim, name, core, debug):
    cm = g4_units.cm
    mm = g4_units.mm
    # one single hole
    hole = sim.add_volume("Hexagon", f"{name}_collimator_hole")
    hole.height = 5.8 * cm
    hole.radius = 0.15 * cm
    hole.material = "G4_AIR"
    hole.mother = core.name

    # parameterised holes
    holep = RepeatParametrisedVolume(repeated_volume=hole)
    if debug:
        holep.linear_repeat = [10, 10, 1]
    else:
        holep.linear_repeat = [77, 100, 1]

    holep.translation = [7.01481 * mm, 4.05 * mm, 0]
    # do it twice, with the following offset
    holep.offset_nb = 2
    holep.offset = [3.50704 * mm, 2.025 * mm, 0]

    sim.volume_manager.add_volume(holep)
    return holep


def lehr_collimator_repeater(sim, name, core, debug):
    cm = g4_units.cm
    mm = g4_units.mm
    # one single hole
    hole = HexagonVolume(name=f"{name}_collimator_hole")
    hole.height = 3.5 * cm
    hole.radius = 0.075 * cm
    hole.material = "G4_AIR"
    hole.mother = core.name
    hole.build_physical_volume = False
    sim.volume_manager.add_volume(hole)

    # parameterised holes
    holep = RepeatParametrisedVolume(repeated_volume=hole)
    if debug:
        holep.linear_repeat = [30, 30, 1]
    else:
        holep.linear_repeat = [183, 235, 1]

    holep.translation = [2.94449 * mm, 1.7 * mm, 0]

    # do it twice, with the following offset
    holep.offset_nb = 2
    holep.offset = [1.47224 * mm, 0.85 * mm, 0]

    sim.volume_manager.add_volume(holep)
    return holep


def lehr_collimator_repeater2_WIP(sim, name, core, debug):
    cm = g4_units.cm
    mm = g4_units.mm

    # one hole
    hole_a = HexagonVolume(name=f"{name}_collimator_hole_a")
    hole_a.height = 3.5 * cm
    hole_a.radius = 0.075 * cm
    hole_a.material = "G4_AIR"
    hole_a.mother = core.name

    # double hole
    hole = unite_volumes(hole_a, hole_a, translation=[1.47224 * mm, 0.85 * mm, 0])
    sim.volume_manager.add_volume(hole)

    # parameterised holes
    holep = RepeatParametrisedVolume(repeated_volume=hole)
    if debug:
        holep.linear_repeat = [30, 30, 1]
    else:
        holep.linear_repeat = [183, 235, 1]

    holep.translation = [2.94449 * mm, 1.7 * mm, 0]
    sim.volume_manager.add_volume(holep)

    return holep


def lehr_collimator_repeater_noparam_WIP(sim, name, core, debug):
    cm = g4_units.cm
    mm = g4_units.mm
    # one single hole
    hole = sim.add_volume("Hexagon", name=f"{name}_collimator_hole")
    hole.height = 3.5 * cm
    hole.radius = 0.075 * cm
    hole.material = "G4_AIR"
    hole.mother = core.name
    translations = []

    if debug:
        linear_repeat = [30, 30, 1]
    else:
        linear_repeat = [183, 235, 1]

    offset_nb = 2
    translation = [2.94449 * mm, 1.7 * mm, 0]
    offset = [1.47224 * mm, 0.85 * mm, 0]
    start = [-(x - 1) * y / 2.0 for x, y in zip(linear_repeat, translation)]
    for i in range(linear_repeat[0]):
        for j in range(linear_repeat[1]):
            for k in range(linear_repeat[2]):
                for o in range(offset_nb):
                    tr_x = start[0] + i * translation[0] + o * offset[0]
                    tr_y = start[1] + j * translation[1] + o * offset[1]
                    tr_z = start[2] + k * translation[2] + o * offset[2]
                    tr = [tr_x, tr_y, tr_z]
                    translations.append(tr)
    hole.translation = translations  # repeated

    return hole


def add_simplified_digitizer_tc99m_OLD(
    sim, crystal_volume_name, output_name, scatter_flag=False
):
    # units
    keV = g4_units.keV
    # default  channels
    channels = []
    if scatter_flag:
        channels = [
            {
                "name": f"scatter_{crystal_volume_name}",
                "min": 114 * keV,
                "max": 126 * keV,
            }
        ]
    channels.append(
        {
            "name": f"peak140_{crystal_volume_name}",
            "min": 126 * keV,
            "max": 154.55 * keV,
        }
    )
    proj = add_digitizer_OLD(sim, crystal_volume_name, channels)
    # output
    proj.output_filename = output_name
    return proj


def add_digitizer_OLD(sim, crystal_volume_name, channels):
    # units
    mm = g4_units.mm
    cc = add_digitizer_energy_windows_OLD(sim, crystal_volume_name, channels)

    # projection
    proj = sim.add_actor(
        "DigitizerProjectionActor", f"Projection_{crystal_volume_name}"
    )
    proj.attached_to = cc.attached_to
    proj.input_digi_collections = [x["name"] for x in cc.channels]
    # proj.spacing = [4.41806 * mm, 4.41806 * mm]
    proj.spacing = [5 * mm, 5 * mm]
    proj.size = [128, 128]

    return proj


def add_digitizer_energy_windows_OLD(sim, crystal_volume_name, channels):
    # Hits
    hc = sim.add_actor("DigitizerHitsCollectionActor", f"Hits_{crystal_volume_name}")
    hc.attached_to = crystal_volume_name
    # no output by default
    hc.output_filename = None
    hc.attributes = [
        "PostPosition",
        "TotalEnergyDeposit",
        "PreStepUniqueVolumeID",
        "GlobalTime",
    ]

    # Singles
    sc = sim.add_actor("DigitizerAdderActor", f"Singles_{crystal_volume_name}")
    sc.attached_to = hc.attached_to
    sc.input_digi_collection = hc.name
    sc.policy = "EnergyWinnerPosition"
    sc.output_filename = None

    # energy windows
    cc = sim.add_actor(
        "DigitizerEnergyWindowsActor", f"EnergyWindows_{crystal_volume_name}"
    )
    cc.attached_to = sc.attached_to
    cc.input_digi_collection = sc.name
    cc.channels = channels
    cc.output_filename = None

    return cc


def add_digitizer_tc99m_OLD(sim, crystal_name, name, spectrum_channel=True):
    # create main chain
    mm = g4_units.mm
    digitizer = Digitizer(sim, crystal_name, name)

    # Singles
    sc = digitizer.add_module("DigitizerAdderActor", f"{name}_singles")
    sc.group_volume = None
    sc.policy = "EnergyWinnerPosition"

    # detection efficiency
    ea = digitizer.add_module("DigitizerEfficiencyActor", f"{name}_eff")
    ea.efficiency = 0.86481  # FAKE

    # energy blurring
    keV = g4_units.keV
    eb = digitizer.add_module("DigitizerBlurringActor", f"{name}_blur")
    eb.blur_attribute = "TotalEnergyDeposit"
    eb.blur_method = "InverseSquare"
    eb.blur_resolution = 0.063  # FAKE
    eb.blur_reference_value = 140.57 * keV

    # spatial blurring
    sb = digitizer.add_module("DigitizerSpatialBlurringActor", f"{name}_sp_blur")
    sb.blur_attribute = "PostPosition"
    sb.blur_fwhm = 7.6 * mm  # FAKE
    sb.keep_in_solid_limits = True
    sb.use_truncated_Gaussian = False

    # energy windows (Energy range. 35-588 keV)
    cc = digitizer.add_module("DigitizerEnergyWindowsActor", f"{name}_energy_window")
    channels = [
        {"name": f"spectrum", "min": 3 * keV, "max": 160 * keV},
        {"name": f"scatter", "min": 108.57749938965 * keV, "max": 129.5924987793 * keV},
        {"name": f"peak140", "min": 129.5924987793 * keV, "max": 150.60751342773 * keV},
    ]
    if not spectrum_channel:
        channels.pop(0)
    cc.channels = channels

    # projection
    proj = digitizer.add_module("DigitizerProjectionActor", f"{name}_projection")
    channel_names = [c["name"] for c in channels]
    proj.input_digi_collections = channel_names
    proj.spacing = [2.21 * mm * 2, 2.21 * mm * 2]
    proj.size = [128, 128]

    # end
    return digitizer


def add_digitizer_tc99m_v2_OLD(sim, crystal_name, name, spectrum_channel=True):
    # create the main chain
    mm = g4_units.mm
    digitizer = Digitizer(sim, crystal_name, name)

    # Singles
    sc = digitizer.add_module("DigitizerAdderActor", f"{name}_singles")
    sc.group_volume = None
    sc.policy = "EnergyWinnerPosition"

    # detection efficiency
    # ea = digitizer.add_module("DigitizerEfficiencyActor", f"{name}_eff")
    # ea.efficiency = 0.86481 # FAKE

    # energy blurring
    keV = g4_units.keV
    eb = digitizer.add_module("DigitizerBlurringActor", f"{name}_blur")
    eb.blur_attribute = "TotalEnergyDeposit"
    eb.blur_method = "InverseSquare"
    eb.blur_resolution = 0.063  # FAKE
    eb.blur_reference_value = 140.57 * keV

    # spatial blurring
    sb = digitizer.add_module("DigitizerSpatialBlurringActor", f"{name}_sp_blur")
    sb.blur_attribute = "PostPosition"
    sb.blur_fwhm = 3 * mm  # FAKE
    sb.keep_in_solid_limits = True
    sb.use_truncated_Gaussian = False

    # energy windows (Energy range. 35-588 keV)
    cc = digitizer.add_module("DigitizerEnergyWindowsActor", f"{name}_energy_window")
    channels = [
        {"name": f"spectrum", "min": 3 * keV, "max": 160 * keV},
        {"name": f"scatter", "min": 108.57749938965 * keV, "max": 129.5924987793 * keV},
        {"name": f"peak140", "min": 129.5924987793 * keV, "max": 150.60751342773 * keV},
    ]
    if not spectrum_channel:
        channels.pop(0)
    cc.channels = channels

    # projection
    proj = digitizer.add_module("DigitizerProjectionActor", f"{name}_projection")
    channel_names = [c["name"] for c in channels]
    proj.input_digi_collections = channel_names
    proj.spacing = [2.21 * mm * 2, 2.21 * mm * 2]
    proj.size = [128, 128]
    proj.write_to_disk = True

    # here, we need this rotation
    proj.detector_orientation_matrix = Rotation.from_euler(
        "yx", (0, 180), degrees=True  # 0 180 => like intevo
    ).as_matrix()

    # end
    return digitizer


def add_digitizer_lu177_OLD(sim, crystal_name, name, spectrum_channel=True):
    # create main chain
    mm = g4_units.mm
    digitizer = Digitizer(sim, crystal_name, name)

    # Singles
    sc = digitizer.add_module("DigitizerAdderActor", f"{name}_singles")
    sc.group_volume = None
    sc.policy = "EnergyWinnerPosition"

    # detection efficiency
    ea = digitizer.add_module("DigitizerEfficiencyActor")
    ea.efficiency = 0.86481  # FAKE

    # energy blurring
    keV = g4_units.keV
    eb = digitizer.add_module("DigitizerBlurringActor")
    eb.blur_attribute = "TotalEnergyDeposit"
    eb.blur_method = "InverseSquare"
    eb.blur_resolution = 0.063  # FAKE
    eb.blur_reference_value = 140.57 * keV
    # eb.blur_resolution = 0.13
    # eb.blur_reference_value = 80 * keV
    # eb.blur_slope = -0.09 * 1 / MeV  # fixme unsure about unit

    # spatial blurring
    # Source: HE4SPECS - FWHM = 3.9 mm
    # FWHM = 2.sigma.sqrt(2ln2) -> sigma = 1.656 mm
    sb = digitizer.add_module("DigitizerSpatialBlurringActor")
    sb.blur_attribute = "PostPosition"
    sb.blur_fwhm = 7.6 * mm  # FAKE
    sb.keep_in_solid_limits = True
    sb.use_truncated_Gaussian = False

    # energy windows (Energy range. 35-588 keV)
    cc = digitizer.add_module("DigitizerEnergyWindowsActor", f"{name}_energy_window")
    keV = g4_units.keV
    # 112.9498 keV  = 6.20 %
    # 208.3662 keV  = 10.38 %
    p1 = 112.9498 * keV
    p2 = 208.3662 * keV
    channels = [
        {"name": "spectrum", "min": 35 * keV, "max": 588 * keV},
        *energy_windows_peak_scatter("peak113", "scatter1", "scatter2", p1, 0.2, 0.1),
        *energy_windows_peak_scatter("peak208", "scatter3", "scatter4", p2, 0.2, 0.1),
    ]
    if not spectrum_channel:
        channels.pop(0)
    cc.channels = channels

    # projection
    proj = digitizer.add_module("DigitizerProjectionActor", f"{name}_projection")
    channel_names = [c["name"] for c in channels]
    proj.input_digi_collections = channel_names
    proj.spacing = [2.21 * mm * 2, 2.21 * mm * 2]
    proj.size = [128, 128]
    proj.write_to_disk = True

    # end
    return digitizer


def add_digitizer_lu177_v2_OLD(sim, crystal_name, name, spectrum_channel=True):
    # create main chain
    mm = g4_units.mm
    digitizer = Digitizer(sim, crystal_name, name)

    # Singles
    sc = digitizer.add_module("DigitizerAdderActor", f"{name}_singles")
    sc.group_volume = None
    sc.policy = "EnergyWinnerPosition"

    # energy blurring
    keV = g4_units.keV
    eb = digitizer.add_module("DigitizerBlurringActor")
    eb.blur_attribute = "TotalEnergyDeposit"
    eb.blur_method = "InverseSquare"
    eb.blur_resolution = 0.063  # FAKE
    eb.blur_reference_value = 140.57 * keV

    # spatial blurring
    # Source: HE4SPECS - FWHM = 3.9 mm
    # FWHM = 2.sigma.sqrt(2ln2) -> sigma = 1.656 mm
    sb = digitizer.add_module("DigitizerSpatialBlurringActor")
    sb.blur_attribute = "PostPosition"
    sb.blur_fwhm = 3.9 * mm  # FAKE
    sb.keep_in_solid_limits = True
    sb.use_truncated_Gaussian = False

    # energy windows (Energy range. 35-588 keV)
    cc = digitizer.add_module("DigitizerEnergyWindowsActor", f"{name}_energy_window")
    keV = g4_units.keV
    # 112.9498 keV  = 6.20 %
    # 208.3662 keV  = 10.38 %
    p1 = 112.9498 * keV
    p2 = 208.3662 * keV
    channels = [
        {"name": "spectrum", "min": 35 * keV, "max": 588 * keV},
        *energy_windows_peak_scatter("peak113", "scatter1", "scatter2", p1, 0.2, 0.1),
        *energy_windows_peak_scatter("peak208", "scatter3", "scatter4", p2, 0.2, 0.1),
    ]
    if not spectrum_channel:
        channels.pop(0)
    cc.channels = channels

    # projection
    proj = digitizer.add_module("DigitizerProjectionActor", f"{name}_projection")
    channel_names = [c["name"] for c in channels]
    proj.input_digi_collections = channel_names
    proj.spacing = [2.21 * mm * 2, 2.21 * mm * 2]
    proj.size = [128, 128]
    proj.write_to_disk = True

    # end
    return digitizer


def add_digitizer_lu177_v3_OLD(sim, crystal_name, name, spectrum_channel=True):
    digitizer = add_digitizer_lu177_v2_OLD(sim, crystal_name, name, spectrum_channel)

    # here, we need this rotation
    proj = digitizer.find_module_by_type("DigitizerProjectionActor")
    proj.detector_orientation_matrix = Rotation.from_euler(
        "yx", (0, 180), degrees=True  # 0 180 => like intevo
    ).as_matrix()

    # end
    return digitizer


def compute_plane_position_and_distance_to_crystal(collimator_type):
    sim = Simulation()
    spect, colli, crystal = add_spect_head(sim, "spect", collimator_type, debug=True)
    pos = get_volume_bounding_box_coordinate_in_frame(
        sim, "spect", "collimator_psd", "max", axis=2
    )
    y = get_volume_bounding_box_coordinate_in_frame(
        sim, "spect", "crystal", "min", axis=2
    )
    crystal_distance = pos - y
    psd = spect.size[2] / 2.0 - pos
    return pos, crystal_distance, psd


def get_plane_position_and_distance_to_crystal_OLD(collimator_type):
    """
    This has been computed with t043_distances or compute_plane_position_and_distance_to_crystal
    - first : distance from head center to the PSD (translation for the plane)
    - second: distance from PSD to center of the crystal
    - third : distance from the head boundary to the PSD (for spect_radius info)
    """
    if collimator_type == "lehr":
        return 61.1, 47.875, 33.9

    if collimator_type == "megp":
        return 84.1, 70.875, 10.9

    if collimator_type == "hegp":
        return 92.1, 78.875, 2.9

    fatal(
        f'Unknown collimator type "{collimator_type}", please use lehr or megp or hegp'
    )


def set_head_orientation(head, collimator_type, radius, gantry_angle_deg=0):
    # pos is the distance from entrance detection plane and head boundary
    pos, _, _ = compute_plane_position_and_distance_to_crystal(collimator_type)
    distance = radius + pos
    # rotation X180 is to set the detector head-foot
    # rotation Z90 is the gantry angle
    r1 = Rotation.from_euler("X", 90, degrees=True)
    r2 = Rotation.from_euler("Z", gantry_angle_deg, degrees=True)
    r = r2 * r1
    head.translation = r.apply([0, 0, -distance])
    head.rotation = r.as_matrix()
    return r


def add_detection_plane_for_arf_OLD(
    sim, plane_size, colli_type, radius, gantry_angle_deg=0, det_name=None
):
    if det_name is None:
        det_name = "arf_plane"

    # rotation ? no
    r = Rotation.from_euler("yx", (0, 0), degrees=True)

    # plane
    nm = g4_units.nm
    detector_plane = sim.add_volume("Box", det_name)
    detector_plane.material = "G4_Galactic"
    detector_plane.color = [1, 0, 0, 1]
    detector_plane.size = [plane_size[0], plane_size[1], 1 * nm]

    # (fake) initial head rotation
    head = Box()
    head.translation = None
    head.rotation = None
    ri = set_head_orientation(head, colli_type, radius, gantry_angle_deg)

    # orientation
    detector_plane.rotation = (ri * r).as_matrix()
    detector_plane.translation = ri.apply([0, 0, -radius])

    return detector_plane


def get_normal_to_arf_plane():
    return [0, 0, 1]


def get_normal_to_detector():
    return [0, 0, -1]


def add_detection_plane_for_arf(sim, det_name, colli_type, plane_size=None):
    # the plane is in the world coordinate system outside the real spect head box.

    # user plane size only for debug purpose
    mm = g4_units.mm
    if plane_size is None:
        plane_size = [576 * mm, 446 * mm]

    # plane
    nm = g4_units.nm
    detector_plane = sim.add_volume("Box", det_name)
    detector_plane.material = "G4_Galactic"
    detector_plane.color = [1, 0, 0, 1]
    detector_plane.size = [plane_size[0], plane_size[1], 1 * nm]

    # compute the position according to the front psd
    p = get_geometrical_parameters()
    arf_position = p[colli_type].psd
    detector_plane.translation = [0, -arf_position, 0]

    # initial_rotation like the detector
    r = Rotation.from_euler("x", -90, degrees=True)
    detector_plane.rotation = r.as_matrix()

    # DEBUG
    """fake = sim.add_volume("Box", "fake")
    fake.mother = detector_plane
    fake.material = "G4_Galactic"
    fake.color = [1, 1, 0, 1]
    fake.size = [20 * mm, 10 * mm, 2 * mm]
    fake.translation = [-plane_size[0] / 2, -plane_size[1] / 2, 0]"""

    # rotate
    rotate_gantry(detector_plane, radius=0, start_angle_deg=0)
    return detector_plane


def add_source_for_arf_training_dataset(
    sim, source_name, activity, detector_plane, min_energy, max_energy
):
    cm = g4_units.cm
    source = sim.add_source("GenericSource", source_name)
    source.particle = "gamma"
    source.activity = activity
    source.position.type = "disc"
    source.position.radius = 5 * cm
    source.position.translation = [0, -20 * cm, 0]
    source.direction.type = "iso"
    source.energy.type = "range"
    source.energy.min_energy = min_energy
    source.energy.max_energy = max_energy
    source.direction.angular_acceptance.target_volumes = [detector_plane.name]
    source.direction.angular_acceptance.enable_intersection_check = True

    return source


def add_actor_for_arf_training_dataset(sim, colli_type, ene_win_actor, rr):
    # the detector is in front of the spect head volume, outside
    detector_plane = add_detection_plane_for_arf(sim, "arf_plane", colli_type)

    # arf actor for building the training dataset
    arf = sim.add_actor("ARFTrainingDatasetActor", "ARF (training)")
    arf.energy_windows_actor = ene_win_actor.name
    arf.attached_to = detector_plane.name
    arf.output_filename = "arf_training_dataset.root"
    arf.russian_roulette = rr
    arf.plane_axis = [0, 1, 2]  # the depth is plane_axis[2] = 2

    return detector_plane, arf


def add_arf_detector(sim, name, colli_type, image_size, image_spacing, pth_filename):
    # plane_size = [image_size[0] * image_spacing[0], image_size[1] * image_spacing[1]]
    # print(f"plane_size: {plane_size}")
    det_plane = add_detection_plane_for_arf(sim, det_name=name, colli_type=colli_type)

    # set the position in front of the collimator
    p = get_geometrical_parameters()
    crystal_distance = p[colli_type].crystal_distance

    arf = sim.add_actor("ARFActor", f"{name}_arf")
    arf.attached_to = det_plane.name
    arf.output_filename = f"projection_{arf.name}.mhd"
    arf.batch_size = 1e5
    arf.image_size = image_size
    arf.image_spacing = image_spacing
    arf.verbose_batch = False
    print(f"crystal_distance: {crystal_distance}")
    arf.distance_to_crystal = crystal_distance
    arf.pth_filename = pth_filename
    arf.flip_plane = False
    arf.plane_axis = [0, 1, 2]
    arf.enable_hit_slice = False
    arf.gpu_mode = "auto"

    return det_plane, arf


def rotate_gantry(head, radius, start_angle_deg, step_angle_deg=1, nb_angle=1):
    # compute the nb translation and rotation
    # WARNING: use the initial rotation and translation of the head.
    translations = []
    rotations = []
    current_angle_deg = start_angle_deg
    for r in range(nb_angle):
        tr = head.translation.copy()
        initial_rotation = head.rotation
        tr[1] += radius
        t, rot = get_transform_orbiting(tr, "Z", current_angle_deg)
        rot = Rotation.from_matrix(rot)
        rot = rot.as_matrix()
        rot = np.matmul(rot, initial_rotation)
        translations.append(t)
        rotations.append(rot)
        current_angle_deg += step_angle_deg

    # set the motion for the SPECT head
    if nb_angle > 1:
        head.add_dynamic_parametrisation(translation=translations, rotation=rotations)
    # we set the initial position in all cases, this allows for check_overlap to be done
    # with the first position
    head.translation = translations[0]
    head.rotation = rotations[0]


def add_actor_for_arf_training_dataset_OLD(sim, head, colli_type, ene_win_actor, rr):
    nm = g4_units.nm
    cm = g4_units.cm

    # detector input plane
    pos, crystal_dist, psd = get_plane_position_and_distance_to_crystal_OLD(colli_type)
    pos += 1 * nm  # to avoid overlap
    detector_plane = sim.add_volume("Box", "arf_plane")
    detector_plane.mother = head
    detector_plane.size = [57.6 * cm, 44.6 * cm, 1 * nm]
    detector_plane.translation = [0, 0, pos]
    detector_plane.material = "G4_Galactic"
    detector_plane.color = [1, 0, 0, 1]

    # arf actor for building the training dataset
    arf = sim.add_actor("ARFTrainingDatasetActor", "ARF (training)")
    arf.attached_to = detector_plane.name
    arf.output_filename = "arf_training_dataset.root"
    arf.energy_windows_actor = ene_win_actor.name
    arf.russian_roulette = rr

    return detector_plane, arf


def add_arf_detector_OLD(
    sim, radius, gantry_angle, size, spacing, colli_type, name, i, pth
):
    plane_size = [size[0] * spacing[0], size[1] * spacing[1]]
    det_plane = add_detection_plane_for_arf_OLD(
        sim,
        plane_size,
        colli_type=colli_type,
        radius=radius,
        gantry_angle_deg=gantry_angle,
        det_name=f"{name}_{i}",
    )

    pos, crystal_distance, psd = compute_plane_position_and_distance_to_crystal(
        colli_type
    )

    arf = sim.add_actor("ARFActor", f"{name}_arf_{i}")
    arf.attached_to = det_plane.name
    arf.output_filename = f"projection_{i}.mhd"
    arf.batch_size = 1e5
    arf.image_size = size
    arf.image_spacing = spacing
    arf.verbose_batch = False
    arf.distance_to_crystal = crystal_distance  # 74.625 * mm
    arf.pth_filename = pth
    arf.flip_plane = True  # because the training was backside
    arf.enable_hit_slice = False
    arf.gpu_mode = "auto"

    return det_plane, arf


def get_pytomography_detector_physics_data(colli_name):
    cm = g4_units.cm
    # create a fake simulation to get the volume information
    sim = Simulation()
    det, colli, crystal = add_spect_head(sim, f"fake", collimator_type=colli_name)
    holep = sim.volume_manager.find_volumes("collimator_hole_param")[0]
    hole = sim.volume_manager.find_volumes("collimator_hole")[0]
    d = {
        "hole_shape": 6,
        "hole_diameter": hole.radius * 2 / cm,
        "hole_spacing": holep.translation[1] / cm,
        "collimator_thickness": hole.height / cm,
        "collimator_material": colli.material.lower(),
        "crystal_width": crystal.size[1] / cm,
        "crystal_height": crystal.size[2] / cm,
    }

    return d


def get_default_size_and_spacing():
    mm = g4_units.mm
    return [128, 128], [2.21 * mm * 2, 2.21 * mm * 2]


def add_digitizer(
    sim, crystal_name, name=None, size=None, spacing=None, channels=None, filename=None
):
    # default parameters
    mm = g4_units.mm
    if name is None:
        name = crystal_name
    if size is None:
        size = get_default_size_and_spacing()[0]
    if spacing is None:
        spacing = get_default_size_and_spacing()[1]
    if channels is None:
        channels = get_default_energy_windows("tc99m")

    # create the main digitizer chain
    digitizer = Digitizer(sim, crystal_name, name)

    # Singles
    sc = digitizer.add_module("DigitizerAdderActor", f"{name}_singles")
    sc.group_volume = None
    sc.policy = "EnergyWinnerPosition"

    # detection efficiency
    # ea = digitizer.add_module("DigitizerEfficiencyActor")
    # ea.efficiency = 0.86481  # FAKE

    # energy blurring
    keV = g4_units.keV
    eb = digitizer.add_module("DigitizerBlurringActor", f"{name}_eblur")
    eb.blur_attribute = "TotalEnergyDeposit"
    eb.blur_method = "InverseSquare"
    eb.blur_resolution = 0.063  # in %, FAKE !
    eb.blur_reference_value = 140.57 * keV

    # spatial blurring
    sb = digitizer.add_module("DigitizerSpatialBlurringActor", f"{name}_sblur")
    sb.blur_attribute = "PostPosition"
    sb.blur_fwhm = 3 * mm  # FAKE !
    sb.keep_in_solid_limits = True
    sb.use_truncated_Gaussian = False

    # default energy windows (Energy range. 35-588 keV)
    cc = digitizer.add_module("DigitizerEnergyWindowsActor", f"{name}_energy_window")
    cc.channels = channels

    # projection
    proj = digitizer.add_module("DigitizerProjectionActor", f"{name}_projection")
    channel_names = [c["name"] for c in channels]
    proj.input_digi_collections = channel_names
    proj.spacing = spacing
    proj.size = size
    proj.write_to_disk = True
    if filename is not None:
        proj.output_filename = filename

    # projection plane: it depends on how the spect device is described
    # here, we need this rotation
    proj.detector_orientation_matrix = Rotation.from_euler(
        "yx", (0, 180), degrees=True  # 0 180 => like intevo
    ).as_matrix()

    return digitizer
