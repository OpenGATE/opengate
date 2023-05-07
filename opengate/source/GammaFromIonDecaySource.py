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

        # binning for the TAC
        user_info.tac_bins = 200

        # write log in the given file
        user_info.dump_log = None

        # write all extracted gammas info in the given file
        user_info.write_to_file = None

        # read gammas info in the given file
        user_info.load_from_file = None

        # this is required because used before init
        user_info.ui_sub_sources = None
        user_info.daughters = None
        user_info.log = ""

        # need to compute the gamma lines before the G4 init
        user_info.initialize_before_g4_engine = build_ui_sub_sources

    def __del__(self):
        pass

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
            update_tac_activity_ui(ui, g4_source)
            # check
            self.check_confine(ui)
            # final initialize
            g4_source.InitializeUserInfo(ui.__dict__)

        # FIXME
        # FIXME
        # FIXME
        # FIXME
        # FIXME

        # integrate TAC, compute all gamma lines
        # extract largest lines
        all_w = []
        all_ene = []
        i = 0
        total_ac = 0
        Bq = gate.g4_units("Bq")
        duration = self.user_info.end_time - self.user_info.start_time
        sec = gate.g4_units("s")
        print(
            "duration = ",
            self.user_info.start_time,
            self.user_info.end_time,
            duration / sec,
        )
        """for s in self.ui_sub_sources:
            intensity = np.sum(s.tac_activities[i]) / self.user_info.activity
            print("source", s.name, self.user_info.activity / Bq, intensity)
            print("t = ", intensity / Bq)
            print("counts  = ", (intensity / Bq) / (duration / sec))
            total_ac += (intensity / Bq) / (duration / sec)"""

        for s in self.ui_sub_sources:
            print("source", s.name)
            intensity = np.sum(s.tac_activities[i]) / self.user_info.activity
            print("intensity % ", intensity)
            w = list(np.array(s.energy.spectrum_weight) * intensity)
            ene = s.energy.spectrum_energy
            all_w += w
            all_ene += ene
            i += 1
        print("size ", len(all_w))
        all_w = np.array(all_w)
        all_ene = np.array(all_ene)
        ind = np.argsort(all_w)
        # ind = np.argsort(all_ene)
        print(ind)
        sorted_w = all_w[ind]
        sorted_ene = all_ene[ind]
        for w, ene in zip(sorted_w, sorted_ene):
            print(f"{ene} MeV     {w}")

        if self.user_info.dump_log is not None:
            with open(self.user_info.dump_log, "w") as outfile:
                outfile.write(self.log)


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


def read_sub_sources_from_file(filename):
    with open(filename) as infile:
        s = infile.read()
        data = jsonpickle.decode(s)
    return data


def build_ui_sub_sources(ui):
    # consider the user ion
    words = ui.particle.split(" ")
    if not ui.particle.startswith("ion") or len(words) != 3:
        gate.fatal(
            f"The 'ion' option of user_info must be 'ion Z A', while it is {ui.ion}"
        )
    z = int(words[1])
    a = int(words[2])

    # read from file ?
    read_data = None
    if ui.load_from_file:
        read_data = read_sub_sources_from_file(ui.load_from_file)

    # get list of decay ions
    id = int(f"{z:3}{a:3}0000")
    first_nuclide = rd.Nuclide(id)
    ui.daughters = get_all_nuclide_progeny(first_nuclide)
    ui.log += f"Initial nuclide : {first_nuclide.nuclide}   z={z} a={a}\n"
    if ui.load_from_file:
        ui.log += f"Read from file {ui.load_from_file} \n"
    ui.log += f"Daughters {len(ui.daughters)}\n\n"

    # loop to add all sources, we copy all options and update the info
    ui.ui_sub_sources = []
    data_to_save = {}
    for daughter in ui.daughters:
        nuclide = daughter.nuclide
        ion_gamma_daughter = Box({"z": nuclide.Z, "a": nuclide.A})
        ui.log += f"{nuclide.nuclide} z={nuclide.Z} a={nuclide.A} "
        if read_data is None:
            ene, w = gate.get_ion_gamma_channels(ion_gamma_daughter)
        else:
            n = daughter.nuclide.nuclide
            if not n in read_data:
                ui.log += f" no gamma. Ignored\n"
                continue
            ene = read_data[n]["ene"]
            w = read_data[n]["w"]

        if len(ene) == 0:
            ui.log += f" no gamma. Ignored\n"
            continue
        ui.log += f" {len(ene)} gammas, with total weights = {np.sum(w)*100:.2f}%\n"
        s = copy.deepcopy(ui)
        s.ui_sub_sources = None
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

        # output ?
        if ui.write_to_file is not None:
            n = daughter.nuclide.nuclide
            data_to_save[n] = {}
            data_to_save[n]["ene"] = ene
            data_to_save[n]["w"] = w

    # save to file ?
    if ui.write_to_file is not None:
        jsonpickle.handlers.registry.register(np.ndarray, NumpyArrayHandler)
        frozen = jsonpickle.encode(data_to_save)
        with open(ui.write_to_file, "w") as outfile:
            outfile.write(frozen)
