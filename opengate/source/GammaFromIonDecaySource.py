from .GenericSource import *
from .helpers_gammas_from_ions_decay import *


class GammaFromIonDecaySource(GenericSource):
    """
    Manage a set of sources, one for each nuclide gamma lines, for all daughters of the given ion.
    Each source will have:
    - activity managed by a TAC, corresponding to the Bateman equation during the time range
    - spectrum energy line for isomeric transition
    - spectrum energy line for atomic relaxation (fluo)
    """

    type_name = "GammaFromIonDecaySource"

    @staticmethod
    def set_default_user_info(user_info):
        gate.GenericSource.set_default_user_info(user_info)

        # specific user_info
        user_info.verbose = False

        # binning for the TAC
        user_info.tac_bins = 200

        # write log in the given file
        user_info.dump_log = None

        # write all extracted gammas info in the given file
        user_info.write_to_file = None

        # read gammas info in the given file
        user_info.load_from_file = None

        # these are not user parameters, but it is required
        # because they are used before init
        user_info.ui_sub_sources = []
        user_info.daughters = None
        user_info.log = ""

        # both are needed, but can be disabled for debug
        user_info.atomic_relaxation_flag = False  ## FIXME set to True
        user_info.isomeric_transition_flag = True

        # need to compute the gamma lines before the G4 init
        user_info.initialize_before_g4_engine = gate.gid_build_all_sub_sources

    def __del__(self):
        pass

    def __getstate__(self):
        # superclass getstate
        super().__getstate__()
        # remove all elements that cannot be pickled
        self.g4_sub_sources = None  # needed
        self.ui_sub_sources = None  # needed
        self.daughters = None  # needed
        self.user_info.ui_sub_sources = None  # needed
        self.user_info.daughters = None  # needed
        return self.__dict__

    def __init__(self, user_info):
        # retrieve from the 'initialize_before_g4_engine' fct
        self.ui_sub_sources = user_info.ui_sub_sources
        self.daughters = user_info.daughters
        # all g4 sources
        self.g4_sub_sources = []
        # log to write
        self.log = user_info.log
        super().__init__(user_info)

    def create_g4_source(self):
        # create all sub sources (one per decaying ion)
        for _ in range(len(self.ui_sub_sources)):
            self.g4_sub_sources.append(g4.GateGenericSource())
        return self.g4_sub_sources[0]

    def initialize(self, run_timing_intervals):
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
            update_tac_activity_ui(ui, g4_source)
            self.check_ui_activity(ui)
            # check
            self.check_confine(ui)
            # final initialize
            g4_source.InitializeUserInfo(ui.__dict__)

        # integrate TAC, compute all gamma lines
        # extract largest lines
        all_w = []
        all_ene = []
        i = 0
        for s in self.ui_sub_sources:
            print("sub source ", i, s.name)
            print()
            intensity = np.sum(s.tac_activities[i]) / self.user_info.activity
            w = list(np.array(s.energy.spectrum_weight) * intensity)
            ene = s.energy.spectrum_energy
            all_w += w
            all_ene += list(ene)
            print("UNCLEAR WHAT TO DO HERE ?", len(all_ene))
            i += 1

        if self.user_info.dump_log is not None:
            with open(self.user_info.dump_log, "w") as outfile:
                outfile.write(self.log)

    def add_to_source_manager(self, source_manager):
        for g4_source in self.g4_sub_sources:
            source_manager.AddSource(g4_source)


def update_tac_activity_ui(ui, g4_source):
    if ui.tac_times is None and ui.tac_activities is None:
        return
    n = len(ui.tac_times)
    if n != len(ui.tac_activities):
        gate.fatal(
            f"option tac_activities must have the same size than tac_times in source '{ui.name}'"
        )

    # scale the activity if energy_spectrum is given (because total may not be 100%)
    total = sum(ui.energy.spectrum_weight)
    sec = gate.g4_units("s")
    Bq = gate.g4_units("Bq")
    ui.tac_activities = np.array(ui.tac_activities) * total

    # it is important to set the starting time for this source as the tac
    # may start later than the simulation timing
    i = 0
    while i < len(ui.tac_activities) and ui.tac_activities[i] <= 0:
        i += 1
    if i >= len(ui.tac_activities):
        # gate.warning(f"Source '{ui.name}' TAC with zero activity.")
        ui.start_time = ui.end_time + 1 * sec
    else:
        ui.start_time = ui.tac_times[i]
        ui.activity = ui.tac_activities[i]
        g4_source.SetTAC(ui.tac_times, ui.tac_activities)

    if ui.verbose:
        print(
            f"GammaFromIon source {ui.name}    total = {total*100:8.2f}%   "
            f" gammas lines = {len(ui.energy.spectrum_weight)}   "
            f" total activity = {sum(ui.tac_activities)/Bq:10.3f}"
            f" first activity = {ui.tac_activities[0]/Bq:4.3f}"
        )
