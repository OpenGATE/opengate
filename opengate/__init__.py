# This file handles the way opengate is imported.

"""
import colored
import threading
print(
    colored.stylize(
        f"Importing opengate (thread " f"{threading.get_native_id()}) ... ",
        colored.fore("dark_gray"),
    ),
    end="",
    flush=True,
)
print(colored.stylize("done", colored.fore("dark_gray")))
"""

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
import opengate.geometry.materials
import opengate.geometry.solids
import opengate.geometry.utility
import opengate.geometry.volumes

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

# import opengate.postprocessors

# These objects are imported at the top level of the package
# because users will frequently use them
from opengate.managers import Simulation
from opengate.managers import create_sim_from_json
from opengate.utility import g4_units
