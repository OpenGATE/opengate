# This file handles the way opengate is imported.

import colored
import threading

print(
    colored.stylize(
        f"Importing opengate (thread " f"{threading.get_native_id()}) ... ",
        colored.fg("dark_gray"),
    ),
    end="",
    flush=True,
)

# These objects are imported at the top level of the package
# because users will frequently use them
from opengate.managers import Simulation
from opengate.utility import g4_units

# the following modules are imported respecting the package structure
# they will be available via
# `import opengate`
# `opengate.xxx.yyy`
# Modules that are mainly for internal use, such as runtiming.py or uisessions.py
# are not automatically imported. If a user needs them, s/he must import
# them specifically, e.g. `import opengate.uisessions`

# subpackages
import opengate.sources
import opengate.geometry
import opengate.actors
import opengate.contrib

# modules directly under /opengate/
import opengate.managers
import opengate.utility
import opengate.logger
import opengate.exception
import opengate.runtiming
import opengate.definitions
import opengate.userhooks
import opengate.image
import opengate.physics
import opengate.base
import opengate.engines


# The following lines make sure that all classes which
# inherit from the GateObject base class are processed upon importing opengate.
# In this way, all properties corresponding to the class's user_info dictionary
# will be created.
# This ensures, e.g., that auto-completion in interactive python consoles
# and code editors suggests the properties.
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
print(colored.stylize("done", colored.fg("dark_gray")))
