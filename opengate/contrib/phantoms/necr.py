from opengate.utility import g4_units


# colors (similar to the ones of Gate)
red = [1, 0, 0, 1]
blue = [0, 0, 1, 1]
green = [0, 1, 0, 1]
yellow = [0.9, 0.9, 0.3, 1]
gray = [0.5, 0.5, 0.5, 1]
white = [1, 1, 1, 0.8]


def add_necr_phantom(sim, name="necr"):
    """
    Simple NECR phantom with a cylinder and linear source
    (geometry part only, the source is defined in the other function)
    """

    # unit
    mm = g4_units.mm
    cm = g4_units.cm

    # ring volume
    phantom = sim.add_volume("Tubs", name)
    phantom.mother = "world"
    phantom.rmax = 103 * mm
    phantom.rmin = 0 * mm
    phantom.dz = 71 * cm / 2.0
    phantom.material = "G4_AIR"
    phantom.color = gray

    # polyethylene cylinder scat
    cylinderScat = sim.add_volume("Tubs", f"{name}_cylinderScat")
    cylinderScat.mother = phantom.name
    cylinderScat.translation = [0, 0, 0]
    cylinderScat.rmax = 102 * mm
    cylinderScat.rmin = 0 * mm
    cylinderScat.dz = 70 * cm / 2.0
    cylinderScat.material = "G4_POLYETHYLENE"
    cylinderScat.color = gray

    # line source interior
    linear_source_in = sim.add_volume("Tubs", f"{name}_linear_source_in")
    linear_source_in.mother = cylinderScat.name
    linear_source_in.translation = [0, -4.5 * cm, 0]
    linear_source_in.rmax = 1.6 * mm
    linear_source_in.rmin = 0 * mm
    linear_source_in.dz = 70 * cm / 2.0
    linear_source_in.material = "G4_WATER"
    linear_source_in.color = red

    # line source exterior
    linear_source_out = sim.add_volume("Tubs", f"{name}_linear_source_out")
    linear_source_out.mother = cylinderScat.name
    linear_source_out.translation = [0, -4.5 * cm, 0]
    linear_source_out.rmax = 2.5 * mm
    linear_source_out.rmin = 1.6 * mm
    linear_source_out.dz = 70 * cm / 2.0
    linear_source_out.material = "G4_POLYETHYLENE"
    linear_source_out.color = red

    return phantom


def add_necr_source(sim, necr_phantom):
    """
    The source is attached to the linear_source_in volume,
    it means its coordinate system is the same
    (not the shape).
    """

    v = sim.volume_manager.volumes[f"{necr_phantom.name}_linear_source_in"]

    src = sim.add_source("GenericSource", f"{necr_phantom.name}_source")
    src.mother = v.name
    src.particle = "e+"
    src.energy.type = "F18"
    src.position.type = "cylinder"
    src.position.radius = v.rmax
    src.position.dz = v.dz
    src.direction.type = "iso"

    return src


def add_necr_source_debug(sim, name):
    """
    The source is described according to the world
    """

    mm = g4_units.mm
    MeV = g4_units.MeV
    src = sim.add_source("GenericSource", name)

    src.particle = "gamma"
    src.energy.type = "mono"
    src.energy.mono = 0.511 * MeV
    src.position.type = "sphere"
    src.position.radius = 1.6 * mm

    """
    src.particle = "e+"
    src.energy.type = "F18_analytic"
    src.position.type = "cylinder"
    src.position.radius = 1.6 * mm
    src.position.dz = 35 * cm
    src.position.translation = [0, -4.5 * cm, 0]
    """
    src.direction.type = "iso"

    return src
