# for a unclear reason, ssl must be imported before to avoid error:
# "from http.client import HTTPConnection, HTTPSConnection
# ImportError: cannot import name 'HTTPSConnection' from 'http.client'"

# generic helpers
from .geometry.Volumes import __world_name__
from .helpers_log import *
from .helpers import *
from .helpers_image import *
from .helpers_tests import *
from .helpers_tests_root import *
from .geometry.helpers_transform import *
from .helpers_beamline import *
from .helpers_rt_plan import *

# main mechanism for the 'elements': source, actor, volume
from .UserInfo import *
from .UserElement import *
from .source.SourceBase import *
from .actor.ActorBase import *
from .geometry.Volumes import *
from .source.TreatmentPlanSource import *

# main object
from .Simulation import *
from .EngineBase import *
from .SimulationEngine import *
from .SimulationOutput import *
from .helpers_run_timing import *
from .GateObjects import *

# helpers to list all possible types of elements
from .geometry.helpers_geometry import *
from .geometry.helpers_materials import *
from .source.helpers_source import *
from .actor.helpers_actor import *
from .actor.helpers_filter import *
from .SimulationUserInfo import *
from .helpers_element import *

# Volume specific
from .geometry.MaterialBuilder import *
from .geometry.ElementBuilder import *
from .geometry.MaterialDatabase import *
from .geometry.VolumeManager import *
from .geometry.VolumeEngine import *

# Source specific
from .source.SourceManager import *
from .source.SourceEngine import *
from .source.GANSourceConditionalGenerator import *
from .source.GANSourceConditionalPairsGenerator import *
from .source.VoxelizedSourceConditionGenerator import *
from .source.PencilBeamSource import *
from .physics.helpers_physics import *
from opengate.physics.helpers_physics import *

# Actor specific
from .actor.FilterManager import *
from .actor.ActorManager import *
from .actor.ActorEngine import *
from .actor.ActionEngine import *
from .UIsessionSilent import *
from .UIsessionVerbose import *
from .RunAction import *

# Physics
from .physics.PhysicsUserInfo import *
from .physics.PhysicsManager import *
from .physics.PhysicsEngine import *
from .physics.Region import *
from .physics.PhysicsConstructors import UserLimitsPhysics
