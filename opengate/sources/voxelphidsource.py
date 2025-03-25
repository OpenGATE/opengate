import itk
import opengate_core as g4
from .generic import GenericSource
from .phidsources import PhotonFromIonDecaySource, get_tac_from_decay, \
    update_sub_source_tac_activity, get_nuclide_progeny, isomeric_transition_load, atomic_relaxation_load
from .voxelsources import VoxelSource
from ..image import read_image_info, update_image_py_to_cpp, compute_image_3D_CDF
from ..utility import ensure_filename_is_str, g4_units, LazyModuleLoader
from ..base import process_cls
from box import Box
import numpy as np

rd = LazyModuleLoader("radioactivedecay")
pandas = LazyModuleLoader("pandas")


class VoxelPhidSource(VoxelSource, PhotonFromIonDecaySource):
    """
    A hybrid source combining VoxelSource and PhotonFromIonDecaySource.
    - Uses a 3D activity distribution from an ITK image (like VoxelSource).
    - Generates gamma rays from ion decay (like PhotonFromIonDecaySource), including
      isomeric transitions and atomic relaxation, with TAC based on Bateman equations.
    - Sub-sources inherit the voxel-based position distribution from the mother source.
    """

    #user_info_defaults = dict(VoxelSource.user_info_defaults)
    #user_info_defaults.update(
    #    {k: v for k, v in PhotonFromIonDecaySource.user_info_defaults.items() if
    #     k not in VoxelSource.user_info_defaults}
    #)

    def __init__(self, *args, **kwargs):
        self.__initcpp__()
        GenericSource.__init__(self, *args, **kwargs)
        self.sub_sources = []
        self.is_a_sub_source = False
        self.itk_image = None
        self.tac_from_decay_parameters = None
        self.daughters = None
        self.log = ""
        self.debug_first_daughter_only = False

    def __initcpp__(self):
        g4.GateVoxelSource.__init__(self)
        g4.GateGenericSource.__init__(self)

    def set_transform_from_user_info(self):
        src_info = read_image_info(str(self.user_info.image))
        pg = self.GetSPSVoxelPosDistribution()
        update_image_py_to_cpp(self.itk_image, pg.cpp_edep_image, False)
        pg.cpp_edep_image.set_spacing(src_info.spacing)
        c = (
                -src_info.size / 2.0 * src_info.spacing
                + self.position.translation
                + src_info.spacing / 2.0
        )
        pg.cpp_edep_image.set_origin(c)

    def cumulative_distribution_functions(self):
        cdf_x, cdf_y, cdf_z = compute_image_3D_CDF(self.itk_image)
        pg = self.GetSPSVoxelPosDistribution()
        pg.SetCumulativeDistributionFunction(cdf_z, cdf_y, cdf_x)

    def initialize(self, run_timing_intervals):
        if not self.user_info.image:
            raise ValueError(f"Image file path is not set for source '{self.name}'. Please specify 'source.image'.")
        image_path = ensure_filename_is_str(self.user_info.image)
        try:
            if not self.is_a_sub_source:
                self.itk_image = itk.imread(image_path)
        except Exception as e:
            raise ValueError(f"Failed to read image file '{image_path}': {str(e)}")

        self.set_transform_from_user_info()
        self.cumulative_distribution_functions()

        if not self.is_a_sub_source:
            if (g4.IsMultithreadedApplication() and g4.G4GetThreadId() == -1) or (
                    not g4.IsMultithreadedApplication()
            ):
                self.build_all_sub_sources()

        GenericSource.initialize(self, run_timing_intervals)
        print(run_timing_intervals)

        self.initialize_start_end_time(run_timing_intervals)
        self.log += f"Simulation time range: {self.start_time} to {self.end_time} seconds\n"

        for sub_source in self.sub_sources:
            sub_source.itk_image = self.itk_image
            sub_source.start_time = self.start_time
            sub_source.end_time = self.end_time
            p = Box(sub_source.tac_from_decay_parameters)
            sub_source.tac_times, sub_source.tac_activities = get_tac_from_decay(
                p.ion_name,
                p.daughter,
                sub_source.activity,
                sub_source.start_time,
                sub_source.end_time,
                p.bins,
            )
            update_sub_source_tac_activity(sub_source)
            sub_source.set_transform_from_user_info()
            sub_source.cumulative_distribution_functions()
            sub_source.InitializeUserInfo(sub_source.user_info)

        if self.user_info.dump_log is not None:
            with open(self.user_info.dump_log, "w") as outfile:
                outfile.write(self.log)

    def add_to_source_manager(self, source_manager):
        for g4_source in self.sub_sources:
            source_manager.AddSource(g4_source)

    def build_all_sub_sources(self):
        words = self.particle.split(" ")
        if not self.particle.startswith("ion") or len(words) != 3:
            raise ValueError(f"The 'ion' option must be 'ion Z A', got {self.particle}")
        z = int(words[1])
        a = int(words[2])

        id = int(f"{z:3}{a:3}0000")
        first_nuclide = rd.Nuclide(id)
        self.daughters = get_nuclide_progeny(first_nuclide)
        self.log += f"Initial nuclide: {first_nuclide.nuclide}   z={z} a={a}\n"
        self.log += f"Daughters: {len(self.daughters)}\n\n"

        if self.isomeric_transition_flag:
            self.build_sub_sources_isomeric_transition(first_nuclide)

        if self.atomic_relaxation_flag:
            self.build_sub_sources_atomic_relaxation(first_nuclide)

        if not self.isomeric_transition_flag and not self.atomic_relaxation_flag:
            raise ValueError(
                f"Error: 'isomeric_transition_flag' or 'atomic_relaxation_flag' "
                f"must be True for source {self.name}"
            )

    def build_sub_sources_isomeric_transition(self, first_nuclide):
        for daughter in self.daughters:
            ene, w = isomeric_transition_load(daughter.nuclide)
            s = self.build_one_sub_source("isomeric_transition", daughter, ene, w, first_nuclide)
            if s:
                self.sub_sources.append(s)

    def build_sub_sources_atomic_relaxation(self, first_nuclide):
        for daughter in self.daughters:
            ene, w = atomic_relaxation_load(daughter.nuclide)
            if len(ene) > 0:
                s = self.build_one_sub_source("atomic_relaxation", daughter, ene, w, first_nuclide)
                if s:
                    self.sub_sources.append(s)

    def build_one_sub_source(self, stype, daughter, ene, w, first_nuclide):
        nuclide = daughter.nuclide
        self.log += f"{nuclide.nuclide} {stype} z={nuclide.Z} a={nuclide.A} "
        if len(ene) == 0:
            self.log += "no gamma. Ignored\n"
            return None
        self.log += f"{len(ene)} gammas, total weights = {np.sum(w) * 100:.2f}%\n"

        name = f"{self.name}__{stype}_of_{nuclide.nuclide}"
        s = VoxelPhidSource(name=name)
        s.is_a_sub_source = True
        s.sub_sources = []
        s.user_info.image = self.user_info.image
        s.verbose = self.verbose
        s.particle = "gamma"
        s.energy.type = "spectrum_discrete"
        s.energy.ion_gamma_mother = Box({"z": first_nuclide.Z, "a": first_nuclide.A})
        s.energy.ion_gamma_daughter = Box({"z": nuclide.Z, "a": nuclide.A})
        s.energy.spectrum_weights = w
        s.energy.spectrum_energies = ene
        s.activity = self.activity
        s.n = self.n
        s.tac_from_decay_parameters = {
            "ion_name": first_nuclide,
            "daughter": daughter,
            "bins": self.tac_bins,
        }
        return s


process_cls(VoxelPhidSource)