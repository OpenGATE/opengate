import pathlib
from opengate.managers import Simulation
from opengate.geometry.volumes import RepeatParametrisedVolume, HexagonVolume
from opengate.geometry.utility import (
    translate_point_to_volume,
    get_transform_orbiting,
    vec_g4_as_np,
)
from opengate.actors.digitizers import *
from scipy.spatial.transform import Rotation
from box import Box


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
    pos, crystal_distance, psdd = get_plane_position_and_distance_to_crystal(colli_type)
    pos += 1 * nm
    p = [0, table_shift, -(radius + psdd)]
    return get_transform_orbiting(p, "x", 90)


def add_spect_head(sim, name="spect", collimator_type="lehr", debug=False):
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
        sim.volume_manager.add_material_database(fdb)

    # check overlap
    sim.check_volumes_overlap = False  # set to True for debug

    # spect head
    head, lead_cover = add_spect_box(sim, name)

    # spect head
    crystal = add_crystal(sim, name, lead_cover)

    # spect collimator
    colli = None
    if collimator_type:
        colli = add_collimator(sim, name, head, collimator_type, debug)

    return head, colli, crystal


def distance_to_center_of_crystal(sim, name="spect"):
    lead_cover = sim.volume_manager.volumes[f"{name}_lead_cover"]
    crystal = sim.volume_manager.volumes[f"{name}_crystal"]
    # distance from center to center of crystal
    shielding = sim.volume_manager.volumes[f"{name}_shielding"]
    d = shielding.translation[2] + lead_cover.translation[2] + crystal.translation[2]
    return d


def add_spect_box(sim, name):
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


def add_crystal(sim, name, lead_cover):
    cm = g4_units.cm
    yellow = [1, 1, 0, 1]
    # mono-bloc crystal thickness 3/8 of inch = 0.9525 cm
    # (if 5/8 inch = 1.5875 ; but probably need to translate elements)
    crystal = sim.add_volume("Box", f"{name}_crystal")
    crystal.mother = lead_cover.name
    crystal.size = [54 * cm, 40 * cm, 0.9525 * cm]
    crystal.translation = [0, 0, 4.4625 * cm]
    crystal.material = "NaITl"
    crystal.color = yellow
    return crystal


def add_collimator(sim, name, head, collimator_type, debug):
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
    sim.volume_manager.add_volume(holep)

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

    return holep


def add_simplified_digitizer_tc99m(
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
    proj.output_filename = output_name
    return proj


def add_digitizer(sim, crystal_volume_name, channels):
    # units
    mm = g4_units.mm
    cc = add_digitizer_energy_windows(sim, crystal_volume_name, channels)

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


def add_digitizer_energy_windows(sim, crystal_volume_name, channels):
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


def add_digitizer_tc99m(sim, crystal_name, name):
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

    # spatial blurring
    sb = digitizer.add_module("DigitizerSpatialBlurringActor")
    sb.blur_attribute = "PostPosition"
    sb.blur_fwhm = 7.6 * mm  # FAKE
    sb.keep_in_solid_limits = True

    # energy windows (Energy range. 35-588 keV)
    cc = digitizer.add_module("DigitizerEnergyWindowsActor", f"{name}_energy_window")
    channels = [
        {"name": f"spectrum", "min": 3 * keV, "max": 160 * keV},
        {"name": f"scatter", "min": 108.57749938965 * keV, "max": 129.5924987793 * keV},
        {"name": f"peak140", "min": 129.5924987793 * keV, "max": 150.60751342773 * keV},
    ]
    cc.channels = channels

    # projection
    proj = digitizer.add_module("DigitizerProjectionActor", f"{name}_projection")
    channel_names = [c["name"] for c in channels]
    proj.input_digi_collections = channel_names
    proj.spacing = [2.21 * mm * 2, 2.21 * mm * 2]
    proj.size = [128, 128]

    # end
    return digitizer


def add_digitizer_lu177(sim, crystal_name, name):
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
    cc.channels = channels

    # projection
    proj = digitizer.add_module("DigitizerProjectionActor", f"{name}_projection")
    channel_names = [c["name"] for c in channels]
    proj.input_digi_collections = channel_names
    proj.spacing = [2.21 * mm * 2, 2.21 * mm * 2]
    proj.size = [128, 128]

    # end
    return digitizer


# FIXME : put this elsewhere
def get_volume_position_in_head(sim, spect_name, vol_name, pos="max", axis=2):
    vol = sim.volume_manager.volumes[f"{spect_name}_{vol_name}"]
    pMin, pMax = vol.bounding_limits
    x = pMax
    if pos == "min":
        x = pMin
    if pos == "center":
        x = pMin + (pMax - pMin) / 2.0
    x = vec_g4_as_np(x)
    x = translate_point_to_volume(sim, vol, spect_name, x)
    return x[axis]


def compute_plane_position_and_distance_to_crystal(collimator_type):
    sim = Simulation()
    spect, colli, crystal = add_spect_head(sim, "spect", collimator_type, debug=True)
    pos = get_volume_position_in_head(sim, "spect", "collimator_psd", "max")
    y = get_volume_position_in_head(sim, "spect", "crystal", "center")
    crystal_distance = pos - y
    psd = spect.size[2] / 2.0 - pos
    return pos, crystal_distance, psd


def get_plane_position_and_distance_to_crystal(collimator_type):
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


def add_fake_table(sim, name="table"):
    """
    Add a patient table (fake)
    """

    # unit
    mm = g4_units.mm
    cm = g4_units.cm
    cm3 = g4_units.cm3
    deg = g4_units.deg
    gcm3 = g4_units.g / cm3

    # colors
    red = [1, 0.7, 0.7, 0.8]
    white = [1, 1, 1, 1]

    sim.volume_manager.material_database.add_material_weights(
        f"CarbonFiber", ["C"], [1], 1.78 * gcm3
    )

    # main bed
    table = sim.add_volume("Tubs", f"{name}_table")
    table.mother = "world"
    table.rmax = 439 * mm
    table.rmin = 406 * mm
    table.dz = 200 * cm / 2.0
    table.sphi = 0 * deg
    table.dphi = 70 * deg
    table.translation = [0, 25 * cm, 0]
    table.rotation = Rotation.from_euler("z", -125, degrees=True).as_matrix()
    table.material = "CarbonFiber"
    table.color = white

    # interior of the table
    tablein = sim.add_volume("Tubs", f"{name}_tablein")
    tablein.mother = table.name
    tablein.rmax = 436.5 * mm
    tablein.rmin = 408.5 * mm
    tablein.dz = 200 * cm / 2.0
    tablein.sphi = 0 * deg
    tablein.dphi = 69 * deg
    tablein.translation = [0, 0, 0]
    tablein.rotation = Rotation.from_euler("z", 0.5, degrees=True).as_matrix()
    tablein.material = "G4_AIR"
    tablein.color = red

    return table


def set_head_orientation(head, collimator_type, radius, gantry_angle=0):
    # pos is the distance from entrance detection plane and head boundary
    pos, _, _ = compute_plane_position_and_distance_to_crystal(collimator_type)
    distance = radius + pos
    # rotation X180 is to set the detector head-foot
    # rotation Z90 is the gantry angle
    r1 = Rotation.from_euler("x", 90, degrees=True)
    r2 = Rotation.from_euler("z", gantry_angle, degrees=True)
    r = r2 * r1
    head.translation = r.apply([0, 0, -distance])
    head.rotation = r.as_matrix()
    return r


def add_detection_plane_for_arf(
    sim, plane_size, colli_type, radius, gantry_angle=0, det_name=None
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
    ri = set_head_orientation(head, colli_type, radius, gantry_angle)

    # orientation
    detector_plane.rotation = (ri * r).as_matrix()
    detector_plane.translation = ri.apply([0, 0, -radius])

    return detector_plane
