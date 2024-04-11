from .generic import GenericSource, TemplateSource
from .voxelsources import VoxelsSource
from .gansources import GANSource, GANPairsSource
from .beamsources import IonPencilBeamSource, TreatmentPlanPBSource
from .phspsources import PhaseSpaceSource
from .phidsources import PhotonFromIonDecaySource
from ..utility import make_builders


"""
    List of source types: Generic, Voxels etc

    Energy spectra for beta+ emitters
"""

source_type_names = {
    GenericSource,
    VoxelsSource,
    GANSource,
    GANPairsSource,
    IonPencilBeamSource,
    TemplateSource,
    PhaseSpaceSource,
    TreatmentPlanPBSource,
    PhotonFromIonDecaySource,
}
source_builders = make_builders(source_type_names)
