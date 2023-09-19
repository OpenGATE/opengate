# classes which the user likely wants to call
# import them here as shortcuts
# from .Simulation import Simulation
# from .physics.Region import Region


# __all__ = [
#     'actor',
#     'geometry',
#     'physics',
#     'source'
# ]

from opengate.managers import Simulation

import opengate.managers
import opengate.helpers
import opengate.definitions
import opengate.geometry
import opengate.physics
import opengate.sources
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
import opengate.userhooks
