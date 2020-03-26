from .gam_helpers import *

g_solid_builders = {}

def G4Box_fake_builder(v):
    # check size or half_size in v
    try:
        s = v.size
    except:
        raise_except(f"Cannot find 'size' in volume {v}")
    return v

def G4Sphere_fake_builder(v):
    # check radius
    try:
        s = v.radius
    except:
        raise_except(f"Cannot find 'radius' in volume {v}")

    return v


'''
Global list of solid builder
'''
g_solid_builders['Box'] = G4Box_fake_builder
g_solid_builders['Sphere'] = G4Sphere_fake_builder
