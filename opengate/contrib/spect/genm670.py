import pathlib
from opengate.exception import fatal
from opengate.utility import g4_units

from opengate.geometry.utility import (
    get_volume_bounding_limits,
    translate_point_to_volume,
    get_transform_orbiting,
    vec_g4_as_np,
    build_param_repeater,
)

# unit
cm = g4_units.cm
mm = g4_units.mm
deg = g4_units.deg

# colors
red = [1, 0.7, 0.7, 0.8]
blue = [0.5, 0.5, 1, 0.8]
gray = [0.5, 0.5, 0.5, 1]
white = [1, 1, 1, 1]
yellow = [1, 1, 0, 1]
green = [0, 1, 0, 1]


def get_collimator(rad):
    radionuclides = ["Tc99m", "Lu177", "In111", "I131"]
    ref_collimators = ["lehr", "megp", "megp", "hegp"]
    if rad not in radionuclides:
        fatal(f'The radionuclide "{rad}" is unknown. Known are: {radionuclides}')
    return ref_collimators[radionuclides.index(rad)]


def add_ge_nm67_fake_spect_head(sim, name="spect"):
    spect_length = 19 * cm
    head = sim.add_volume("Box", name)
    head.material = "G4_AIR"
    head.size = [57.6 * cm, 44.6 * cm, spect_length]
    head.color = white
    return head


def get_orientation_for_CT(colli_type, table_shift, radius):
    nm = g4_units.nm
    pos, crystal_distance, psdd = get_plane_position_and_distance_to_crystal(colli_type)
    pos += 1 * nm
    p = [0, table_shift, -(radius + psdd)]
    return get_transform_orbiting(p, "x", 90)


def add_ge_nm67_spect_head(sim, name="spect", collimator_type="lehr", debug=False):
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
    f = pathlib.Path(__file__).parent.resolve()
    fdb = f"{f}/spect_ge_nm670_materials.db"
    if fdb not in sim.volume_manager.material_database.filenames:
        sim.add_material_database(fdb)

    # check overlap
    sim.g4_check_overlap_flag = False  # set to True for debug

    # spect head
    head, lead_cover = add_ge_nm670_spect_box(sim, name, collimator_type)

    # spect head
    crystal = add_ge_nm670_spect_crystal(sim, name, lead_cover)

    # spect collimator
    if collimator_type:
        colli = add_ge_nm670_spect_collimator(sim, name, head, collimator_type, debug)

    return head, crystal


def distance_to_center_of_crystal(sim, name="spect"):
    lead_cover = sim.get_volume_user_info(f"{name}_lead_cover")
    crystal = sim.get_volume_user_info(f"{name}_crystal")
    # distance from center to center of crystal
    shielding = sim.get_volume_user_info(f"{name}_shielding")
    d = shielding.translation[2] + lead_cover.translation[2] + crystal.translation[2]
    return d


def add_ge_nm670_spect_box(sim, name, collimator_type):
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
    reflector.translation = [0, 0, 3.92625 * cm]
    reflector.material = "TiO2"
    reflector.color = green

    # backside
    # The back-side is fairly complex, and may have a strong influence on the
    # spectrum: the model shown here is simplified
    backside = sim.add_volume("Box", f"{name}_backside")
    backside.mother = lead_cover.name
    backside.size = [54 * cm, 40 * cm, 8 * cm]
    backside.translation = [0, 0, -0.13375 * cm]
    backside.material = "Pyrex66"
    backside.color = blue

    return head, lead_cover


def add_ge_nm670_spect_crystal(sim, name, lead_cover):
    # mono-bloc crystal thickness 3/8 of inch = 0.9525 cm
    # (if 5/8 inch = 1.5875 ; but probably need to translate elements)
    crystal = sim.add_volume("Box", f"{name}_crystal")
    crystal.mother = lead_cover.name
    crystal.size = [54 * cm, 40 * cm, 0.9525 * cm]
    crystal.translation = [0, 0, 4.4625 * cm]
    crystal.material = "NaITl"
    crystal.color = yellow
    return crystal


def add_ge_nm670_spect_collimator(sim, name, head, collimator_type, debug):
    """
    Start with default lehr collimator description,
    then change some parameters for the other types
    """

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
    holep = False
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

    return colli_trd


def hegp_collimator_repeater(sim, name, core, debug):
    # one single hole
    hole = sim.add_volume("Hexagon", f"{name}_collimator_hole")
    hole.height = 6.6 * cm
    hole.radius = 0.2 * cm
    hole.material = "G4_AIR"
    hole.mother = core.name

    # parameterised holes
    size = [54, 70, 1]
    if debug:
        size = [10, 10, 1]
    tr = [10.0459 * mm, 5.8 * mm, 0]
    holep = build_param_repeater(sim, core.name, hole.name, size, tr)

    # dot it twice, with the following offset
    holep.offset_nb = 2
    holep.offset = [5.0229 * mm, 2.9000 * mm, 0]

    return holep


def megp_collimator_repeater(sim, name, core, debug):
    # one single hole
    hole = sim.add_volume("Hexagon", f"{name}_collimator_hole")
    hole.height = 5.8 * cm
    hole.radius = 0.15 * cm
    hole.material = "G4_AIR"
    hole.mother = core.name

    # parameterised holes
    size = [77, 100, 1]
    if debug:
        size = [10, 10, 1]
    tr = [7.01481 * mm, 4.05 * mm, 0]
    holep = build_param_repeater(sim, core.name, hole.name, size, tr)

    # do it twice, with the following offset
    holep.offset_nb = 2
    holep.offset = [3.50704 * mm, 2.025 * mm, 0]

    return holep


def lehr_collimator_repeater(sim, name, core, debug):
    # one single hole
    hole = sim.add_volume("Hexagon", f"{name}_collimator_hole")
    hole.height = 3.5 * cm
    hole.radius = 0.075 * cm
    hole.material = "G4_AIR"
    hole.mother = core.name

    # parameterised holes
    size = [183, 235, 1]
    if debug:
        size = [10, 10, 1]
    tr = [2.94449 * mm, 1.7 * mm, 0]
    holep = build_param_repeater(sim, core.name, hole.name, size, tr)

    # do it twice, with the following offset
    holep.offset_nb = 2
    holep.offset = [1.47224 * mm, 0.85 * mm, 0]

    return holep


def UNUSED_megp_collimator_repeater_parametrised(sim, name, core, debug):
    """# because this volume will be parameterised, we need to prevent
    # the creation of the physical volume
    hole.build_physical_volume = False

    # parameterised holes
    holep = sim.add_volume('RepeatParametrised', f'{name}_collimator_hole_param')
    holep.mother = core.name
    holep.translation = None
    holep.rotation = None
    holep.repeated_volume_name = hole.name
    # number of repetition
    holep.linear_repeat = [183, 235, 1]
    if debug:
        holep.linear_repeat = [10, 10, 1]
    # translation for each repetition
    holep.translation = [2.94449 * mm, 1.7 * mm, 0]
    # starting position
    holep.start = [-(holep.linear_repeat[0] * holep.translation[0]) / 2.0,
                   -(holep.linear_repeat[1] * holep.translation[1]) / 2.0, 0]
    """


def add_simplified_digitizer_Tc99m(
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
    proj = add_digitizer(sim, crystal_volume_name, channels)
    # output
    proj.output = output_name
    return proj


def add_digitizer(sim, crystal_volume_name, channels):
    # units
    mm = g4_units.mm
    cc = add_digitizer_energy_windows(sim, crystal_volume_name, channels)

    # projection
    proj = sim.add_actor(
        "DigitizerProjectionActor", f"Projection_{crystal_volume_name}"
    )
    proj.mother = cc.mother
    proj.input_digi_collections = [x["name"] for x in cc.channels]
    # proj.spacing = [4.41806 * mm, 4.41806 * mm]
    proj.spacing = [5 * mm, 5 * mm]
    proj.size = [128, 128]

    return proj


def add_digitizer_energy_windows(sim, crystal_volume_name, channels):
    # Hits
    hc = sim.add_actor("DigitizerHitsCollectionActor", f"Hits_{crystal_volume_name}")
    hc.mother = crystal_volume_name
    hc.output = ""  # No output
    hc.attributes = [
        "PostPosition",
        "TotalEnergyDeposit",
        "PreStepUniqueVolumeID",
        "GlobalTime",
    ]

    # Singles
    sc = sim.add_actor("DigitizerAdderActor", f"Singles_{crystal_volume_name}")
    sc.mother = hc.mother
    sc.input_digi_collection = hc.name
    sc.policy = "EnergyWinnerPosition"
    sc.output = ""  # No output

    # energy windows
    cc = sim.add_actor(
        "DigitizerEnergyWindowsActor", f"EnergyWindows_{crystal_volume_name}"
    )
    cc.mother = sc.mother
    cc.input_digi_collection = sc.name
    cc.channels = channels
    cc.output = ""  # No output
    return cc


def get_volume_position_in_head(sim, spect_name, vol_name, pos="max"):
    vol = sim.get_volume_user_info(f"{spect_name}_{vol_name}")
    pMin, pMax = get_volume_bounding_limits(sim, vol.name)
    x = pMax
    if pos == "min":
        x = pMin
    if pos == "center":
        x = pMin + (pMax - pMin) / 2.0
    x = vec_g4_as_np(x)
    x = translate_point_to_volume(sim, vol, spect_name, x)
    return x[2]


def get_plane_position_and_distance_to_crystal(collimator_type):
    """
    This has been computed with t043_distances
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
