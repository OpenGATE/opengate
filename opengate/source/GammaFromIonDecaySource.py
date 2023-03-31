from .GenericSource import *
from .helpers_gammas_from_ions_decay import *
import copy


class GammaFromIonDecaySource(GenericSource):
    """
    Manage a set of sources, one for each nuclide gamma lines, for all daughters of the given ion.
    Each source will have:
    - activity managed by a TAC, corresponding to the Bateman equation during the time range
    - spectrum energy line
    """

    type_name = "GammaFromIonDecaySource"

    @staticmethod
    def set_default_user_info(user_info):
        gate.GenericSource.set_default_user_info(user_info)
        # specific user_info
        user_info.tac_bins = 200
        user_info.ui_sub_sources = None
        user_info.daughters = None

        # remove some non-used attributes ?
        gate.warning(f"FIXME : remove unused ui attributes ")

        # need to compute the gamma lines before the G4 init
        user_info.initialize_before_g4_engine = build_ui_sub_sources

    def __del__(self):
        pass

    def __init__(self, user_info):
        self.ui_sub_sources = user_info.ui_sub_sources
        self.g4_sub_sources = []
        self.daughters = user_info.daughters
        super().__init__(user_info)

    def create_g4_source(self):
        for _ in self.daughters:
            self.g4_sub_sources.append(g4.GateGenericSource())
        return self.g4_sub_sources[0]

    def initialize(self, run_timing_intervals):
        # FIXME check
        # MUST be ion

        # init timing intervals for all ui
        self.initialize_start_end_time(run_timing_intervals)
        for ui in self.ui_sub_sources:
            ui.start_time = self.user_info.start_time
            ui.end_time = self.user_info.end_time

        # this will initialize and set user_info to the cpp side
        for g4_source, ui in zip(self.g4_sub_sources, self.ui_sub_sources):
            # get tac from decay
            p = Box(ui.tac_from_decay_parameters)
            ui.tac_times, ui.tac_activities = gate.get_tac_from_decay(
                p.ion_name, p.daughter, ui.activity, ui.start_time, ui.end_time, p.bins
            )
            # update the tac
            self.update_tac_activity_ui(ui, g4_source)
            # check
            self.check_confine(ui)
            # final initialize
            g4_source.InitializeUserInfo(ui.__dict__)

    def update_tac_activity_ui(self, ui, g4_source):
        if ui.tac_times is None and ui.tac_activities is None:
            return
        n = len(ui.tac_times)
        if n != len(ui.tac_activities):
            gate.fatal(
                f"option tac_activities must have the same size than tac_times in source '{ui.name}'"
            )

        # scale the activity if energy_spectrum is given (because total may not be 100%)
        total = sum(ui.energy.spectrum_weight)
        ui.tac_activities = np.array(ui.tac_activities) * total

        # it is important to set the starting time for this source as the tac
        # may start later than the simulation timing
        i = 0
        while i < len(ui.tac_activities) and ui.tac_activities[i] <= 0:
            i += 1
        if i >= len(ui.tac_activities):
            gate.warning(f"Source '{ui.name}' TAC with zero activity.")
            sec = gate.g4_units("s")
            ui.start_time = ui.end_time + 1 * sec
        else:
            ui.start_time = ui.tac_times[i]
            ui.activity = ui.tac_activities[i]
            g4_source.SetTAC(ui.tac_times, ui.tac_activities)


def build_ui_sub_sources(ui):
    # consider the user ion
    words = ui.particle.split(" ")
    if not ui.particle.startswith("ion") or len(words) != 3:
        gate.fatal(
            f"The 'ion' option of user_info must be 'ion Z A', while it is {ui.ion}"
        )
    z = int(words[1])
    a = int(words[2])
    # get list of decay ions
    id = int(f"{z:3}{a:3}0000")
    first_nuclide = rd.Nuclide(id)
    print(first_nuclide)
    ui.daughters = get_all_nuclide_progeny(first_nuclide)
    print("nb d", len(ui.daughters))

    # loop to add all sources, we copy all options and update the info
    ui.ui_sub_sources = []
    for daughter in ui.daughters:
        nuclide = daughter.nuclide
        ion_gamma_daughter = Box({"z": nuclide.Z, "a": nuclide.A})
        print(nuclide)
        ene, w = gate.get_ion_gamma_channels(ion_gamma_daughter)
        if len(ene) == 0:
            print(f"Ignoring source {nuclide} because no gammas")
            continue
        s = copy.deepcopy(ui)
        s._name = f"{ui.name}_{daughter.nuclide.nuclide}"
        # additional info, specific to ion gamma source
        s.particle = "gamma"
        # set gamma lines
        s.energy.type = "spectrum_lines"
        s.energy.ion_gamma_mother = Box({"z": z, "a": a})
        s.energy.ion_gamma_daughter = ion_gamma_daughter
        s.energy.spectrum_weight = w
        s.energy.spectrum_energy = ene
        # prepare times and activities that will be set during initialisation
        s.tac_from_decay_parameters = {
            "ion_name": first_nuclide,
            "daughter": daughter,
            "bins": ui.tac_bins,
        }
        ui.ui_sub_sources.append(s)
