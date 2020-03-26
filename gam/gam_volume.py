from .gam_helpers import *
from .gam_solid import *
from box import Box

g_volume_builders = {}

def geometry_build_volume_default(vol):
    print(f'Building a fake G4 Volume {vol.name} {vol.type} ')

    # build solid
    if vol.type not in g_solid_builders:
        s = f"The solid type '{vol.type}' is unknown"
        raise_except(s)
    builder = g_solid_builders[vol.type]
    builder(vol)

    # get material
    # build Logical Volume
    # build Physical Volume  <--- need placement information
    # build region
    # (build Sensitive Detector) <-- later in scorer
    # build visualisation attribute
    # build surface information

    return vol

g_volume_builders['Box'] = geometry_build_volume_default

####

# PhysVol = builder(box)
# default_builder = simple vol/LV/PV
# complex builder for image

# how to add other volume in diff file ?

#list of volume: basic, image(x),

#
# #### alternative ???
# class Volume(Box):
#     def __init__(self, name, vol_type):
#         super().__init__()
#         self.name = name
#         self.vol_type = vol_type
#         print('toto')
#
#     def construct(self):
#         print('construct')
#
