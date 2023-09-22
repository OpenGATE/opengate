# This file handles the way opengate is imported.

# These objects are imported at the top level of the package
# because users will frequently use them
from opengate.managers import Simulation
from opengate.helpers import g4_units

# the following modules are imported respecting the package structure
# they will be available via
# `import opengate`
# `opengate.xxx.yyy`
# Modules that are mainly for internal use, such as runtiming.py or uisessions.py
# are not automatically imported. If a user needs them, s/he must import
# them specifically, e.g. `import opengate.uisessions`
import opengate.managers
import opengate.helpers
import opengate.logger
import opengate.exception
import opengate.definitions
import opengate.userhooks
import opengate.image
import opengate.geometry
import opengate.geometry.materials
import opengate.geometry.utility
import opengate.physics
import opengate.sources
import opengate.sources.generic
import opengate.sources.beamlines
import opengate.sources.beamsources
import opengate.sources.phspsources
import opengate.sources.tpssources
import opengate.sources.voxelsources
import opengate.actors
import opengate.actors.digitizers
import opengate.actors.doseactors
import opengate.actors.miscactors
import opengate.actors.filters
import opengate.base

# The following lines make sure that all classes which
# inherit from the GateObject base class are processed upon importing opengate.
# In this way, all properties corresponding to the class's user_info dictionary
# will be created.
# This ensures, e.g., that auto completion in interactive python consoles
# and code editors suggests the propeties.
opengate.base.process_cls(opengate.managers.PhysicsListManager)
opengate.base.process_cls(opengate.managers.PhysicsManager)
opengate.base.process_cls(opengate.physics.Region)


# It is also possible to define an __all__ variable
# to specify what a wildcard import such as
# `from opengate import *`
# will import.
#
# # __all__ = [
#     'actor',
#     'geometry',
#     'physics',
#     'source'
# ]
