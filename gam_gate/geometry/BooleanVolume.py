import gam_gate as gam
import gam_g4 as g4
from box import Box
from scipy.spatial.transform import Rotation

rid = Rotation.identity().as_matrix()

bool_operators = ['union', 'subtraction', 'intersection']


def solid_union(a, b, tr=None, rot=rid):
    if tr is None:
        tr = [0, 0, 0]
    return solid_bool('union', a, b, tr, rot)


def solid_subtraction(a, b, tr=None, rot=rid):
    if tr is None:
        tr = [0, 0, 0]
    return solid_bool('subtraction', a, b, tr, rot)


def solid_intersection(a, b, tr=None, rot=rid):
    if tr is None:
        tr = [0, 0, 0]
    return solid_bool('intersection', a, b, tr, rot)


def solid_bool(ope, a, b, tr, rot):
    s = Box()
    s[ope] = Box()
    s.name = f'{a.name}_{ope}_{b.name}'
    s[ope].a = a
    s[ope].b = b
    s[ope].translation = tr
    s[ope].rotation = rot
    return s


class BooleanVolume(gam.VolumeBase):
    """
    https://geant4-userdoc.web.cern.ch/UsersGuides/ForApplicationDeveloper/html/Detector/Geometry/geomSolids.html?highlight=boolean#solids-made-by-boolean-operations
    """

    type_name = 'Boolean'

    def __init__(self, name):
        gam.VolumeBase.__init__(self, name)
        # default values
        self.user_info.nodes = []
        # short
        self.user_info.add_node = \
            lambda x, y, z=Rotation.identity().as_matrix(): self.add_node(x, y, z)
        # keep all created solids
        self.solid = self.user_info.solid  # None
        self.g4_solids = []

    def set_solid(self, solid):
        self.solid = solid

    def add_node(self, solid, translation=None, rotation_matrix=rid):
        if translation is None:
            translation = [0, 0, 0]
        b = Box()
        b.solid = solid
        b.translation = translation
        b.rotation = rotation_matrix
        self.user_info.nodes.append(b)

    def build_solid(self):  ## FIXME change the name (VolBase.build_suild
        return self._build_one_solid(self.solid)

    def _build_one_solid(self, solid):
        # could be simple, or starting with union etc
        if isinstance(solid, Box):
            for op in bool_operators:
                if op in solid:
                    return self._build_solid_bool(solid.name, op, solid[op])
        # build a 'fake' solid/volume to get the build_solid function
        # add the key 'i_am_a_solid' to avoid key checking
        solid.i_am_a_solid = True
        vol = gam.new_element(solid)
        return vol.build_solid()

    def _build_solid_bool(self, name, op, s):
        translation = gam.vec_np_as_g4(s.translation)
        rotation = gam.rot_np_as_g4(s.rotation)
        sa = self._build_one_solid(s.a)
        sb = self._build_one_solid(s.b)
        solid = None
        if op == 'subtraction':
            solid = g4.G4SubtractionSolid(name, sa, sb, rotation, translation)
        if op == 'union':
            solid = g4.G4UnionSolid(name, sa, sb, rotation, translation)
        if op == 'intersection':
            solid = g4.G4IntersectionSolid(name, sa, sb, rotation, translation)
        if not solid:
            gam.fatal(f'Error in _build_solid_bool. Wrong operator ? {op}')
        self.g4_solids.append(sa)
        self.g4_solids.append(sb)
        self.g4_solids.append(solid)
        return solid
