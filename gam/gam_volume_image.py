from .gam_helpers import *
from .gam_solid import *
from box import Box
from .gam_volume import g_volume_builders

def geometry_build_volume_image(vol):
    print('image tot otizeprtzer', vol)

g_volume_builders['Image'] = geometry_build_volume_image
