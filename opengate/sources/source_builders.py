from .generic import GenericSource, TemplateSource
from .voxelsources import VoxelsSource
from .gansources import GANSource, GANPairsSource
from .beamsources import PencilBeamSource
from .phspsources import PhaseSpaceSource
from ..helpers import make_builders


"""
    List of source types: Generic, Voxels etc

    Energy spectra for beta+ emitters
"""

source_type_names = {
    GenericSource,
    VoxelsSource,
    GANSource,
    GANPairsSource,
    PencilBeamSource,
    TemplateSource,
    PhaseSpaceSource,
}
source_builders = make_builders(source_type_names)
