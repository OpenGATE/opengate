from .gam_helpers import *

# static const global list of Solid builders

# Later -> some helpers functions will be there
# Later -> all specific builders will be in separate file

g_solid_builders = {}

def G4Box_fake_builder(v):
    # check size or half_size in v
    try:
        s = v.size
        # here build a G4Box(name, size)
    except:
        raise_except(f"Cannot find 'size' in volume {v}")
    return 'I am a G4Box'


def G4Sphere_fake_builder(v):
    # check radius
    try:
        s = v.radius
        # here build a G4Sphere(name, radius)
    except:
        raise_except(f"Cannot find 'radius' in volume {v}")

    return 'I am a G4Sphere'


'''
Global list of solid builder
'''
g_solid_builders['Box'] = G4Box_fake_builder
g_solid_builders['Sphere'] = G4Sphere_fake_builder
