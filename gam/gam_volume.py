from .gam_solid import *
from box import Box

# global static list of volume builders
g_volume_builders = {}

# Later -> helpers functions will be there
# other specific Volume builder will be in separate file


def geometry_build_volume_default(vol):
    print(f'Building a fake G4 Volume {vol.name} {vol.type} ')

    # all G4 objects will be stored in g4
    vol.g4 = Box()

    # build solid
    if vol.type not in g_solid_builders:
        s = f"The solid type '{vol.type}' is unknown"
        raise_except(s)
    builder = g_solid_builders[vol.type]
    vol.g4.solid = builder(vol)

    # get material

    # build Logical Volume

    # build Physical Volume  <--- need placement information

    # build region

    # (build Sensitive Detector) <-- later in scorer

    # build visualisation attribute

    # build surface information

    return vol

