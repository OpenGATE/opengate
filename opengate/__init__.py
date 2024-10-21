# This file handles the way opengate is imported.
import os
import sys


def restart_with_glibc_tunables():
    """
    Restart the current process with GLIBC_TUNABLES set.
    """
    # tunables_value = "glibc.rtld.optional_static_tls=2048000"
    tunables_value = "glibc.rtld.optional_static_tls=1500000"

    # Check if the environment variable is already set correctly
    if os.environ.get("GLIBC_TUNABLES") != tunables_value:
        # Set the environment variable
        new_env = os.environ.copy()
        new_env["GLIBC_TUNABLES"] = tunables_value

        # Restart the process with the new environment
        os.execve(sys.executable, [sys.executable] + sys.argv, new_env)

        # Exit the current process
        sys.exit()


if sys.platform.startswith("linux"):
    restart_with_glibc_tunables()

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
from opengate.base import help_on_user_info
