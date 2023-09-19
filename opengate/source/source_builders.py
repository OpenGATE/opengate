from .GenericSource import GenericSource
from .VoxelsSource import VoxelsSource
from .GANSource import GANSource
from .GANPairsSource import GANPairsSource
from .PencilBeamSource import PencilBeamSource
from .TemplateSource import TemplateSource
from .PhaseSpaceSource import PhaseSpaceSource
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
