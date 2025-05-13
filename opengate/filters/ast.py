import ast
import inspect
import sys
from typing import Callable, Any
from ..utility import g4_units
import opengate_core as g4


# make local variables for each G4 unit
# TODO define guideline for unit naming when * or /
for key in g4_units:
    locals().update({key: g4_units[key]})


def dbgp(s):
    print(f"[dbgp] {s}", file=sys.stderr)
    return True


class Attribute:
    name: str
    get: Callable[[g4.G4Step], Any]

    def __init__(self, name, get):
        self.name = name
        self.get = get


##################################################
# Energy
total_energy_deposit = Attribute("total_energy_deposit", g4.GetAttrTotalEnergyDeposit)
post_kinetic_energy = Attribute("post_kinetic_energy", g4.GetAttrPostKineticEnergy)
pre_kinetic_energy = Attribute("pre_kinetic_energy", g4.GetAttrPreKineticEnergy)
kinetic_energy = Attribute("kinetic_energy", g4.GetAttrKineticEnergy)
track_vertex_kinetic_energy = Attribute(
    "track_vertex_kinetic_energy", g4.GetAttrTrackVertexKineticEnergy
)
event_kinetic_energy = Attribute("event_kinetic_energy", g4.GetAttrEventKineticEnergy)

# Time
local_time = Attribute("local_time", g4.GetAttrLocalTime)
global_time = Attribute("global_time", g4.GetAttrGlobalTime)
pre_global_time = Attribute("pre_global_time", g4.GetAttrPreGlobalTime)
time_from_begin_of_event = Attribute(
    "time_from_begin_of_event", g4.GetAttrTimeFromBeginOfEvent
)
track_proper_time = Attribute("track_proper_time", g4.GetAttrTrackProperTime)

# Misc
weight = Attribute("weight", g4.GetAttrWeight)
track_id = Attribute("track_id", g4.GetAttrTrackID)
parent_id = Attribute("parent_id", g4.GetAttrParentID)
event_id = Attribute("event_id", g4.GetAttrEventID)
run_id = Attribute("run_id", g4.GetAttrRunID)
thread_id = Attribute("thread_id", g4.GetAttrThreadID)
track_creator_process = Attribute(
    "track_creator_process", g4.GetAttrTrackCreatorProcess
)
track_creator_model_name = Attribute(
    "track_creator_model_name", g4.GetAttrTrackCreatorModelName
)
track_creator_model_index = Attribute(
    "track_creator_model_index", g4.GetAttrTrackCreatorModelIndex
)
process_defined_step = Attribute("process_defined_step", g4.GetAttrProcessDefinedStep)
particle_name = Attribute("particle_name", g4.GetAttrParticleName)
parent_particle_name = Attribute("parent_particle_name", g4.GetAttrParentParticleName)
particle_type = Attribute("particle_type", g4.GetAttrParticleType)
track_volume_name = Attribute("track_volume_name", g4.GetAttrTrackVolumeName)
track_volume_copy_no = Attribute("track_volume_copy_no", g4.GetAttrTrackVolumeCopyNo)
pre_step_volume_copy_no = Attribute(
    "pre_step_volume_copy_no", g4.GetAttrPreStepVolumeCopyNo
)
post_step_volume_copy_no = Attribute(
    "post_step_volume_copy_no", g4.GetAttrPostStepVolumeCopyNo
)
track_volume_instance_id = Attribute(
    "track_volume_instance_id", g4.GetAttrTrackVolumeInstanceID
)
pre_step_unique_volume_id = Attribute(
    "pre_step_unique_volume_id", g4.GetAttrPreStepUniqueVolumeID
)
post_step_unique_volume_id = Attribute(
    "post_step_unique_volume_id", g4.GetAttrPostStepUniqueVolumeID
)
pdg_code = Attribute("pdg_code", g4.GetAttrPDGCode)
hit_unique_volume_id = Attribute("hit_unique_volume_id", g4.GetAttrHitUniqueVolumeID)

# Position
position = Attribute("position", g4.GetAttrPosition)
post_position = Attribute("post_position", g4.GetAttrPostPosition)
pre_position = Attribute("pre_position", g4.GetAttrPrePosition)
pre_position_local = Attribute("pre_position_local", g4.GetAttrPrePositionLocal)
post_position_local = Attribute("post_position_local", g4.GetAttrPostPositionLocal)
event_position = Attribute("event_position", g4.GetAttrEventPosition)
track_vertex_position = Attribute(
    "track_vertex_position", g4.GetAttrTrackVertexPosition
)

# Direction
direction = Attribute("direction", g4.GetAttrDirection)
post_direction = Attribute("post_direction", g4.GetAttrPostDirection)
pre_direction = Attribute("pre_direction", g4.GetAttrPreDirection)
pre_direction_local = Attribute("pre_direction_local", g4.GetAttrPreDirectionLocal)
track_vertex_momentum_direction = Attribute(
    "track_vertex_momentum_direction", g4.GetAttrTrackVertexMomentumDirection
)
event_direction = Attribute("event_direction", g4.GetAttrEventDirection)

# Polarization
polarization = Attribute("polarization", g4.GetAttrPolarization)

# Length
step_length = Attribute("step_length", g4.GetAttrStepLength)
track_length = Attribute("track_length", g4.GetAttrTrackLength)

# Scatter information
unscattered_primary_flag = Attribute(
    "unscattered_primary_flag", g4.GetAttrUnscatteredPrimaryFlag
)
##################################################


class FilterASTTransformer(ast.NodeTransformer):
    def fn_name_from_attr(self, node):
        f_src = inspect.getsource(eval(ast.unparse(node)).get)
        tree = ast.parse(f_src)
        f_name = tree.body[0].name
        return f_name

    def visit_Name(self, node):
        node_type = eval(f"type({node.id})")
        if node_type is Attribute:
            # Method 1 -- using local functions
            # f_name = self.fn_name_from_attr(node)
            # func = ast.Name(id=f"{f_name}", ctx=ast.Load())

            # Method 2 -- using opengate_core functions
            fn = eval(ast.unparse(node)).get
            print(fn.__module__)

            func = ast.Attribute(
                value=ast.Name(id="opengate_core", ctx=ast.Load()),
                attr=fn.__name__,
                ctx=ast.Load(),
            )

            args = [ast.Name(id="step", ctx=ast.Load())]

            return ast.Call(func=func, args=args, keywords=[])
        else:
            value_types = (bool, int, float, str, type(None))
            value = eval(ast.unparse(node))
            if isinstance(value, value_types):
                return ast.Constant(value=value)

            return node

    # resolve constant computations (e.g. 5 * MeV)
    def visit_BinOp(self, node: ast.BinOp):
        self.generic_visit(node)
        if isinstance(node.left, ast.Constant) and isinstance(node.right, ast.Constant):
            value = eval(ast.unparse(node))
            return ast.Constant(value=value)
        else:
            return node

    def visit_Expr(self, node: ast.Expr):
        self.generic_visit(node)
        return node

    def visit_Compare(self, node: ast.Compare):
        self.generic_visit(node)
        return node
