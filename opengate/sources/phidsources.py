from ..logger import NONE
from ..exception import fatal, warning
from ..utility import g4_units, LazyModuleLoader
from .generic import GenericSource
import opengate_core as g4
import opengate as gate

import math
import re
from box import Box
import jsonpickle
import numpy as np
import pathlib
import urllib
import copy
import os
import inspect

# the following packages seems to take a bit of time to load
rd = LazyModuleLoader("radioactivedecay")
pandas = LazyModuleLoader("pandas")


class PhotonFromIonDecaySource(GenericSource):
    """
    Manage a set of sources, one for each nuclide gamma lines, for all daughters of the given ion.
    Each source will have:
    - activity managed by a TAC, corresponding to the Bateman equation during the time range
    - spectrum energy line for isomeric transition
    - spectrum energy line for atomic relaxation (fluo)
    """

    type_name = "PhotonFromIonDecaySource"

    @staticmethod
    def set_default_user_info(user_info):
        GenericSource.set_default_user_info(user_info)

        # specific user_info
        user_info.verbose = False

        # binning for the TAC
        user_info.tac_bins = 200

        # write log in the given file
        user_info.dump_log = None

        # these are not user parameters, but it is required
        # because they are used before init
        user_info.ui_sub_sources = []
        user_info.daughters = None
        user_info.log = ""

        # both are needed, but can be disabled for debug
        user_info.atomic_relaxation_flag = True
        user_info.isomeric_transition_flag = True

        # debug
        user_info.debug_first_daughter_only = False

        # need to compute the gamma lines before the G4 init
        user_info.initialize_source_before_g4_engine = gid_build_all_sub_sources

    def __del__(self):
        # print('del source', self.user_info.name)
        pass

    # FIXME
    def __getstate__(self):
        d = super().__getstate__()
        # remove all elements that cannot be pickled
        state = self.__dict__.copy()
        state.update(d)
        state["g4_sub_sources"] = None  # needed
        state["g4_source"] = None  # needed
        state["ui_sub_sources"] = None  # needed
        state["daughters"] = None  # needed
        state["user_info"].ui_sub_sources = None  # needed
        state["user_info"].daughters = None  # needed
        state["simulation"] = None  # needed
        return state

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
            ui.tac_times, ui.tac_activities = get_tac_from_decay(
                p.ion_name, p.daughter, ui.activity, ui.start_time, ui.end_time, p.bins
            )
            # update the tac
            update_tac_activity_ui(ui, g4_source)
            self.check_ui_activity(ui)
            # check
            self.check_confine(ui)
            # final initialize
            g4_source.InitializeUserInfo(ui.__dict__)

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
        fatal(
            f"option tac_activities must have the same size than tac_times in source '{ui.name}'"
        )

    # scale the activity if energy_spectrum is given (because total may not be 100%)
    total = sum(ui.energy.spectrum_weight)
    sec = g4_units.s
    Bq = g4_units.Bq

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
        # IMPORTANT : activities must be x by total here
        # (not before, because it can be called several times in MT mode)
        g4_source.SetTAC(ui.tac_times, np.array(ui.tac_activities) * total)

    if ui.verbose:
        print(
            f"GammaFromIon source {ui.name}    total = {total * 100:8.2f}%   "
            f" gammas lines = {len(ui.energy.spectrum_weight)}   "
            f" total activity = {sum(ui.tac_activities) / Bq:10.3f}"
            f" first activity = {ui.tac_activities[0] / Bq:5.2f}"
            f" last activity = {ui.tac_activities[-1] / Bq:5.2f}"
        )


class PhotonIonDecayIsomericTransitionExtractor:
    """

    For a given ion, extract all possible gamma emission, with corresponding intensity

    1. Create a 'fake' gate simulation because G4 engine must be initialized. This is done
    in a separate process. The function "_get_all_gamma_emissions" is used.

    2. From the IonTable all the Decay Channels are extracted
        -> function '_get_all_decay_channels'

    3. For one decay channel, we look all possible excitation levels
        This is read in the G4 data file G4LEVELGAMMADATA of the corresponding ion
        -> _get_gammas_for_one_channel
        -> _get_gammas_for_one_level

    """

    def __init__(self, z, a, verbose=False):
        """
        WARNING
        PhotonIonDecayIsomericTransitionExtractor does NOT work anymore
        Now PHID extract data from the IAEA database, not directly from G4
        """
        fatal("PhotonIonDecayIsomericTransitionExtractor NOT implemented")

        self.z = z
        self.a = a
        self.channels = None
        self.gammas = []
        self.verbose = verbose
        self.verbose = True  ### FIXME

    def extract(self):
        # we need to create and run a simulation
        # in order to access all G4 constructed objects
        sim = gate.Simulation()
        sim.verbose_level = NONE
        sim.physics_list_name = "G4EmStandardPhysics_option3"
        sim.physics_manager.enable_decay = True
        # sim.add_g4_command_("/particle/nuclideTable/min_halflife 0 ns")
        sim.user_hook_after_init = self._get_all_gamma_emissions
        sim.init_only = True
        s = sim.add_source("GenericSource", "fake")
        s.n = 1  # will not be used because init_only is True, but avoid warning
        # go
        sim.run(start_new_process=True)
        # get output
        self.gammas = sim.user_hook_log[0]  # gammas

    def _get_all_gamma_emissions(self, sim_engine):
        v = self.verbose
        # get all decay channels (first level only)
        self.channels = self._get_all_decay_channels()

        # find gammas for all channels
        v and print(f"There are {len(self.channels)} channels")
        for ch in self.channels:
            self._get_gammas_for_one_channel(ch)

        # merge similar lines
        keV = g4_units.keV
        gamma_final = {}
        v and print()
        v and print(f"Merge")
        # already_done = {}
        for g in self.gammas:
            e = g.transition_energy
            if e in gamma_final:
                # if g.final_intensity in already_done[e]:
                #    print("Do not add twice ???", g.final_intensity, already_done[e])
                # else:
                v and print(
                    f"Add intensities for {e / keV} keV : "
                    f"{gamma_final[e].final_intensity} + {g.final_intensity} for {g}"
                    # f"  (already done = {already_done[e]}"
                )
                gamma_final[e].final_intensity += g.final_intensity
                # already_done[e].append(g.final_intensity)
            else:
                gamma_final[e] = g
                # already_done[e] = [g.final_intensity]
        self.gammas = []
        for g in gamma_final.values():
            self.gammas.append(g)
        self.gammas = sorted(self.gammas, key=lambda x: x["transition_energy"])

        # print
        if v:
            for g in self.gammas:
                print(
                    f"{g['transition_energy'] / keV} keV   = {g['final_intensity'] * 100}%"
                )

        # store output
        sim_engine.user_hook_log.append(self.gammas)

    def _get_all_decay_channels(self):
        # get ion
        ion_table = g4.G4IonTable.GetIonTable()
        ion = ion_table.GetIon(self.z, self.a, 0)

        # get the decay table
        process_table = g4.G4ProcessTable.GetProcessTable()
        decay_process = process_table.FindRadioactiveDecay()
        decay_table = decay_process.GetDecayTable(ion)

        # get all decay channels (first level)
        channels = []
        keV = g4_units.keV
        for i in range(decay_table.entries()):
            channel = decay_table.GetDecayChannel(i)
            for j in range(channel.GetNumberOfDaughters()):
                d = channel.GetDaughter(j)
                n = d.GetParticleName()
                t = d.GetParticleType()
                if n == "alpha" or t != "nucleus":
                    continue
                ch = Box()
                ch.name = str(d.GetParticleName())
                ch.ion = d
                ch.z = d.GetAtomicNumber()
                ch.a = d.GetAtomicMass()
                ch.br = channel.GetBR()
                ch.energy_label = None
                ch.excitation_energy = d.GetExcitationEnergy()
                ch.excitation_energy_label = 0
                # get the energy label
                # This is tricky : in order to retrieve the correct channel
                # we extract the Energy in the name such as Hf177[321.316] -> 321.316
                # then it will be compared to the excitation energy
                result = re.search(r"(.*)\[(.*)\]", ch.name)
                if result:
                    ch.excitation_energy_label = float(result.groups()[1]) * keV
                channels.append(ch)
        return channels

    def _get_gammas_for_one_channel(self, channel):
        v = self.verbose
        if channel.excitation_energy == 0:
            return
        # read database file
        v and print()
        levels = isomeric_transition_read_g4_data(channel.z, channel.a)
        v and print(f"Channel {channel} has {len(levels)} levels")

        # from the name extract the level
        for level in levels.values():
            # We compare label with E as float number
            print(
                f"compare {level.excitation_energy}   to   {channel.excitation_energy_label}"
            )
            if math.isclose(
                level.excitation_energy, channel.excitation_energy_label, rel_tol=1e-9
            ):
                v and print()
                v and print(f"Analysing channel {channel.name}")
                g = self._get_gammas_for_one_level(levels, level, br=channel.br)
                self.gammas = self.gammas + g
                break
            # earlier termination (no need to check other level when too large)
            if level.excitation_energy > channel.excitation_energy_label * 1.1:
                break
        # it can happen that no corresponding level is found
        # for example for z87.a221 Fr221[712.000]
        # 712 keV leads to no gamma

    def _get_gammas_for_one_level(self, levels, level, br, p=1, tab=""):
        g_level = []
        g_level_final = []
        total_p = 0
        if br == 0:
            return g_level_final

        # compute Ig = gamma intensity for all daughters and total Ig
        for d in level.daugthers.values():
            lev = self._level_daughter_info(d)
            if lev is not None:
                g_level.append(lev)
                total_p += lev.transition_intensity * (lev.alpha + 1)

        if total_p == 0:
            return g_level_final

        # compute the relative intensity
        # consider also the branching ratio and 'p' which is the probability in case
        # of fallback from another level
        v = self.verbose
        keV = g4_units.keV
        v and print(
            f"{tab}Level = {level.order_level} E={level.excitation_energy / keV} keV  "
            f"nb_levels = {level.n_gammas}  branching_ratio={br:.5f}    current_proba={p:.5f}"
        )
        tab = f"{tab}    "
        for lev in g_level:
            lev.transition_intensity = (
                (lev.alpha + 1) * lev.transition_intensity / total_p
            )
            # This is the key computation of the probability
            # P = BR x Pg x It x current_p
            # BR = Branching ratio
            # Pg = gamma emission probability
            # It = total transition probability =  Ic + Ig
            # Ig = transition_intensity
            # alpha = Ic/Ig
            lev.final_intensity = (
                lev.prob_gamma_emission * lev.transition_intensity * br * p
            )
            v and print(
                f"{tab}P{level.order_level}->{lev.daughter_order}     E={lev.transition_energy / keV} keV "
                f"br={br:.5f}  It={lev.transition_intensity:.5f} Pg={lev.prob_gamma_emission:.5f}"
                f" p={p:.3f} "
                f"   ->  final intensity={100 * lev.final_intensity:.5f}% "
            )
            g_level_final.append(lev)
            p2 = lev.transition_intensity
            if lev.daughter_order != 0:
                s = str(lev.daughter_order)
                if s in levels:
                    l2 = levels[s]
                    g = self._get_gammas_for_one_level(levels, l2, br, p2, tab)
                    g_level_final = g_level_final + g
                else:
                    warning(f"Unknown level {s}, ignoring ...")
                    continue

        return g_level_final

    def _level_daughter_info(self, d):
        g = Box()
        g.daughter_order = d.daughter_order
        g.transition_energy = d.transition_energy
        g.transition_intensity = d.intensity
        g.alpha = d.alpha
        g.prob_gamma_emission = 1 / (1 + g.alpha)
        return g


def print_phid_info(rad_name, br=1.0, tab=""):
    nuclide = get_nuclide_from_name(rad_name)
    print(
        f"{tab}{nuclide.nuclide}    Z={nuclide.Z} A={nuclide.A}     "
        f"HL={nuclide.half_life('readable')} ({nuclide.half_life('s'):.1f} s)"
        f"     BF={br}"
    )
    progeny = nuclide.progeny()
    brs = nuclide.branching_fractions()
    t = tab + "  "
    for p, b in zip(progeny, brs):
        print_phid_info(p, b, t)
    return nuclide


def get_nuclide_from_name(rad_name):
    try:
        return rd.Nuclide(rad_name)
    except:
        fatal(f"Cannot find nuclide named {rad_name}, try something like 225Ac.")


def get_nuclide_and_direct_progeny(z, a):
    a = int(a)
    z = int(z)
    id = int(f"{z:3}{a:3}0000")
    nuclide = rd.Nuclide(id)
    p = nuclide.progeny()
    return nuclide, p


def get_nuclide_progeny(nuclide, intensity=1.0, parent=None):
    # insert current nuclide
    p = []
    if parent is None:
        a = Box()
        a.nuclide = nuclide
        a.hl = a.nuclide.half_life()
        a.parent = [None]
        a.intensity = intensity
        p.append(a)
    # start a list of daughters
    daughters = nuclide.progeny()
    branching_fractions = nuclide.branching_fractions()
    # loop recursively
    # the intensity is the branching fraction x the current intensity
    # if the rad is already in the list, we add the intensity
    nuc_to_add = []
    i = 0
    for d, br in zip(daughters, branching_fractions):
        a = Box()
        try:
            a.nuclide = rd.Nuclide(d)
        except:
            warning(f"Unknown nuclide {d}, ignoring ...")
            continue
        a.hl = a.nuclide.half_life()
        a.parent = [nuclide]
        a.intensity = intensity * br
        p.append(a)
        aa = get_nuclide_progeny(a.nuclide, intensity=a.intensity, parent=nuclide)
        nuc_to_add += aa
        i = i + 1

    # the daughter's daughters are added after the loop to keep the order
    # also : merge parents
    for aa in nuc_to_add:
        found = next(
            (item for item in p if item.nuclide.nuclide == aa.nuclide.nuclide),
            None,
        )
        if found:
            found.intensity += aa.intensity
            found.parent += aa.parent
            # remove duplicate
            found.parent = list(set(found.parent))
        else:
            p.append(aa)
    return p


# def atomic_relaxation_load(nuclide: rd.Nuclide, load_type="local"):
def atomic_relaxation_load(nuclide, load_type="local"):
    ene_ar, w_ar = None, None
    if load_type == "local":
        ene_ar, w_ar = atomic_relaxation_load_from_file(nuclide.nuclide)
    elif load_type == "iaea":
        filename = atomic_relaxation_get_filename(nuclide.nuclide)
        warning(
            f"Load data for {nuclide.nuclide} from IAEA website and store in : {filename}"
        )
        name = nuclide.nuclide[: nuclide.nuclide.index("-")]
        df = atomic_relaxation_load_from_iaea_website(nuclide.A, name)
        atomic_relaxation_store_to_file(nuclide.nuclide, df)
        ene_ar, w_ar = atomic_relaxation_load_from_file(nuclide.nuclide)
    else:
        df = atomic_relaxation_load_from_data_file(nuclide, load_type)
        atomic_relaxation_store_to_file(nuclide.nuclide, df)
        ene_ar, w_ar = atomic_relaxation_load_from_file(nuclide.nuclide)
    return ene_ar, w_ar


def atomic_relaxation_load_from_data_file_OLD(nuclide, filename):
    # get info
    A = nuclide.A
    Z = nuclide.Z
    N = A - Z

    # read data file
    df = pandas.read_csv(filename, header=0, dtype=str, low_memory=False)
    c = ["z_parent", "n_parent", "z_daughter", "n_daughter"]
    df[c] = df[c].astype(int)

    # Filter lines where the first value is Z and the second value is N
    df = df[(df["z_parent"] == Z) & (df["n_parent"] == N)]
    print(f"Initial number of lines: {len(df)}")

    # Convert energy range into energy lines
    for index, row in df.iterrows():
        e = row["energy"]
        # e = row["energy_num"]
        i = row["intensity_100_dec_of_parent"]
        if "-" in i:
            warning(f"error i = {i}")
            continue
        # separate grouped lines ?
        if "-" in e:
            parts = e.split("-")
            nb = 10
            e1 = float(parts[0].strip())
            e2 = float(parts[1].strip())
            ene_inc = (e2 - e1) / nb
            intv = float(i) / (nb + 1)
            ce = e1
            print(f"Energy range {e} ({e1} {e2})  => {i}")
            for i in range(nb + 1):
                new_row = {"energy": str(ce), "intensity_100_dec_of_parent": str(intv)}
                ce += ene_inc
                df = pandas.concat([df, pandas.DataFrame([new_row])], ignore_index=True)
        else:
            print(f"Energy {e} => {i}")

    # filter: remove rows with range
    df = df[~df["energy"].str.contains("-")]
    df = df[~df["intensity_100_dec_of_parent"].str.contains("-")]

    # rename columns and convert to float
    df = df.rename(
        columns={
            # "energy": "energy_old",
            # "energy_num": "energy",
            "intensity_100_dec_of_parent": "intensity",
        }
    )
    df["intensity"] = df["intensity"].astype(float)
    df["energy"] = df["energy"].astype(float)

    # group by same intensity
    print(f"Before group number of lines: {len(df)}")
    df = df.groupby("energy")["intensity"].sum()
    df = df.reset_index(name="intensity")
    print(f"Total number of lines: {len(df)}")

    return df


def atomic_relaxation_load_from_data_file_NEW1(nuclide, filename):
    # get info
    A = nuclide.A
    Z = nuclide.Z
    N = A - Z

    print(f"A = {A}  Z = {Z}  N = {N}")
    # read data file
    df = pandas.read_csv(filename, header=0, dtype=str, low_memory=False)
    c = ["z_parent", "n_parent", "z_daughter", "n_daughter"]
    df[c] = df[c].astype(int)

    # Filter lines where the first value is Z and the second value is N
    df = df[(df["z_parent"] == Z) & (df["n_parent"] == N)]
    print(f"Initial number of lines: {len(df)}")

    # Convert energy range into energy lines
    """for index, row in df.iterrows():
        e = row["energy"]
        # e = row["energy_num"]
        i = row["intensity_100_dec_of_parent"]
        if "-" in i:
            warning(f"error i = {i}")
            continue
        # separate grouped lines ?
        if "-" in e:
            parts = e.split("-")
            nb = 10
            e1 = float(parts[0].strip())
            e2 = float(parts[1].strip())
            ene_inc = (e2 - e1) / nb
            intv = float(i) / (nb + 1)
            ce = e1
            print(f"Energy range {e} ({e1} {e2})  => {i}")
            for i in range(nb + 1):
                new_row = {"energy": str(ce), "intensity_100_dec_of_parent": str(intv)}
                ce += ene_inc
                df = pandas.concat([df, pandas.DataFrame([new_row])], ignore_index=True)
        else:
            print(f"Energy {e} => {i}")
    """

    # filter: remove rows with range
    print(f"Number of lines = {len(df)} ")
    # df = df[~df["energy"].str.contains("-")]
    # print(f'Number of lines ene- = {len(df)} ')
    df = df[~df["energy_num"].str.contains("-")]
    print(f"Number of lines enenum- = {len(df)} ")
    df = df[~df["intensity_100_dec_of_parent"].str.contains("-")]
    print(f"Number of lines int- = {len(df)} ")

    # rename columns and convert to float
    df = df.rename(
        columns={
            "energy": "energy_old",
            "energy_num": "energy",
            "intensity_100_dec_of_parent": "intensity",
        }
    )
    df["intensity"] = df["intensity"].astype(float)
    df["energy"] = df["energy"].astype(float)

    # group by same intensity
    print(f"Before group number of lines: {len(df)}")
    df = df.groupby("energy")["intensity"].sum()
    df = df.reset_index(name="intensity")
    print(f"Total number of lines: {len(df)}")

    return df


def atomic_relaxation_load_from_data_file(nuclide, filename):
    # get info
    A = nuclide.A
    Z = nuclide.Z
    N = A - Z

    # read data file
    df = pandas.read_csv(filename, header=0, dtype=str, low_memory=False)
    c = ["z_parent", "n_parent", "z_daughter", "n_daughter"]
    df[c] = df[c].astype(int)

    # Filter lines where the first value is Z and the second value is N
    df = df[(df["z_parent"] == Z) & (df["n_parent"] == N)]

    # convert when the intensity is an interval, use the mean
    def convert_to_mean(interval):
        if "-" in interval:
            # Split the interval string and convert values to float
            start, end = map(float, interval.split(" - "))
            # Calculate the mean value
            mean_value = (start + end) / 2
            return mean_value
        else:
            # Return the original value if it's not a string
            return interval

    df["intensity_100_dec_of_parent"] = df["intensity_100_dec_of_parent"].apply(
        convert_to_mean
    )

    # Remove Lx L KA KB and Kx (that are duplicated lines)
    df = df[~df["shell"].str.match(r"^L\d+$")]
    df = df[~df["shell"].str.match(r"^L$")]
    df = df[~df["shell"].str.match(r"^KA$")]
    df = df[~df["shell"].str.match(r"^KB$")]
    df = df[~df["shell"].str.match(r"^K\d+$")]

    # rename columns and convert to float
    df = df.rename(
        columns={
            "energy": "energy_old",
            "energy_num": "energy",
            "intensity_100_dec_of_parent": "intensity",
        }
    )
    df["intensity"] = df["intensity"].astype(float)
    df["energy"] = df["energy"].astype(float)

    # group by same intensity
    df = df.groupby("energy")["intensity"].sum()
    df = df.reset_index(name="intensity")
    print(f"Total number of lines: {len(df)}")

    return df


def atomic_relaxation_load_from_iaea_website(a, rad_name):
    # https://nds.iaea.org/relnsd/vcharthtml/VChartHTML.html
    livechart = "https://nds.iaea.org/relnsd/v1/data?"
    nuclide_name = f"{a}{rad_name}"
    url = livechart + f"fields=decay_rads&nuclides={nuclide_name}&rad_types=x"
    print(url)
    try:
        df = lc_read_csv(url)
        print(df)
    except:
        raise Exception(
            f"Cannot get data for atomic relaxation of {rad_name} with this url : {url}"
        )
    if "intensity" not in df:
        # when there is no xray
        return None
    return df


def atomic_relaxation_get_filename(nuclide_name):
    gate_module = inspect.getfile(inspect.importlib.import_module("opengate"))
    folder = pathlib.Path(os.path.dirname(gate_module)) / "data" / "atomic_relaxation"
    filename = folder / f"{nuclide_name.lower()}.txt"
    return filename


def atomic_relaxation_load_from_file(nuclide_name, filename=None):
    nuclide_name = nuclide_name.lower()
    if filename is None:
        filename = atomic_relaxation_get_filename(nuclide_name)
    try:
        df = pandas.read_csv(filename)
    except pandas.errors.EmptyDataError:
        return [], []
    except FileNotFoundError:
        raise Exception(
            f"During 'load_ion_gamma_atomic_relaxation_nds_iaea' cannot read file"
            f" {nuclide_name}.txt in {filename}"
        )
    try:
        ene, w = atomic_relaxation_get_ene_weights_from_df(df)
    except:
        return [], []
    return ene, w


def atomic_relaxation_store_to_file(nuclide_name, df, filename=None):
    nuclide_name = nuclide_name.lower()
    if filename is None:
        filename = atomic_relaxation_get_filename(nuclide_name)
    warning(f"Store atomic relaxation data for {nuclide_name} in: {filename}")
    if df is not None:
        df.to_csv(filename, index=False)
    else:
        f = open(filename, "w")
        f.close()


def atomic_relaxation_get_ene_weights_from_df(df):
    if df is None:
        return np.array([]), np.array([])
    # remove blanks (unknown intensities)
    df = df[pandas.to_numeric(df["intensity"], errors="coerce").notna()]
    # convert to numeric. Note how one can specify the field by attribute or by string
    keV = g4_units.keV
    df.energy = df["energy"].astype(float)
    df.intensity = df["intensity"].astype(float)
    return df.energy.to_numpy() * keV, df.intensity.to_numpy() / 100


# def atomic_relaxation_load_all_gammas(nuclide: rd.Nuclide):
def atomic_relaxation_load_all_gammas(nuclide):
    daughters = get_nuclide_progeny(nuclide)
    results = []
    for d in daughters:
        ene_ar, w_ar = atomic_relaxation_load(d.nuclide)
        for e, w in zip(ene_ar, w_ar):
            results.append({"energy": e, "intensity": w, "type": "ar", "nuclide": d})
    return results


def lc_read_csv(url):
    req = urllib.request.Request(url)
    req.add_header(
        "User-Agent",
        "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:77.0) Gecko/20100101 Firefox/77.0",
    )
    return pandas.read_csv(urllib.request.urlopen(req))


def isomeric_transition_get_filename(nuclide_name):
    gate_module = inspect.getfile(inspect.importlib.import_module("opengate"))
    folder = pathlib.Path(os.path.dirname(gate_module)) / "data" / "isomeric_transition"
    filename = folder / f"{nuclide_name.lower()}.txt"
    return filename


def isomeric_transition_load(nuclide, filename=None, half_life=None):
    if filename is None:
        filename = isomeric_transition_get_filename(nuclide.nuclide)
    if half_life is None:
        sec = g4_units.s
        half_life = nuclide.half_life("s") * sec
    try:
        ene, w = isomeric_transition_load_from_df_file(
            nuclide.nuclide, half_life=half_life, filename=filename
        )
        return ene, w
    except Exception:
        name = nuclide.nuclide[: nuclide.nuclide.index("-")]
        df = isomeric_transition_load_from_iaea_website(nuclide.A, name)
        isomeric_transition_store_df_to_file(nuclide.nuclide, df, filename)
        ene, w = isomeric_transition_get_ene_weights_from_df(df, half_life=half_life)
        return np.array(ene), np.array(w)


def isomeric_transition_load_OLD(nuclide, filename=None):
    if filename is None:
        filename = isomeric_transition_get_filename(nuclide.nuclide)
    try:
        read_data = isomeric_transition_load_from_file(filename)
        return np.array(read_data["ene"]), np.array(read_data["w"])
    except Exception as exception:
        warning(f"Extract data for {nuclide.nuclide} from G4 and store in : {filename}")
        ene, w = isomeric_transition_extract_from_ion_decay(nuclide)
        data_to_save = {"ene": ene, "w": w}
        isomeric_transition_store(nuclide.nuclide, data_to_save, filename)
        return np.array(ene), np.array(w)


def isomeric_transition_store(nuclide_name, data_to_save, filename):
    jsonpickle.handlers.registry.register(np.ndarray, NumpyArrayHandler)
    frozen = jsonpickle.encode(data_to_save, indent=2)
    warning(f"Store isomeric transition data for {nuclide_name} in: {filename}")
    if filename is None:
        filename = isomeric_transition_get_filename(nuclide_name)
    with open(filename, "w") as outfile:
        outfile.write(frozen)


def isomeric_transition_store_df_to_file(nuclide_name, df, filename=None):
    nuclide_name = nuclide_name.lower()
    if filename is None:
        filename = isomeric_transition_get_filename(nuclide_name)
    if df is not None:
        df.to_csv(filename, index=False)
    else:
        f = open(filename, "w")
        f.close()


def isomeric_transition_load_from_df_file(nuclide_name, half_life, filename=None):
    nuclide_name = nuclide_name.lower()
    if filename is None:
        filename = isomeric_transition_get_filename(nuclide_name)
    try:
        df = pandas.read_csv(filename)
    except pandas.errors.EmptyDataError:
        return [], []
    except FileNotFoundError:
        raise Exception(
            f"During 'isomeric_transition_load_from_df_file' cannot read file"
            f" {nuclide_name}.txt in {filename}"
        )
    ene, w = isomeric_transition_get_ene_weights_from_df(df, half_life=half_life)
    return ene, w


def isomeric_transition_get_ene_weights_from_df(df, half_life):
    if df is None:
        return np.array([]), np.array([])
    # remove blanks (unknown intensities)
    df = df.loc[pandas.to_numeric(df["intensity"], errors="coerce").notna()]
    # remove rows when half life is not the correct one (for example for metastable)
    # we consider all half life values and keep the closest one only
    sec = g4_units.s
    unique_values = df["half_life_sec"].unique()
    if len(unique_values) == 0:
        return [0], [0]
    closest_value = min(unique_values, key=lambda x: abs(x - half_life / sec))
    df = df[df["half_life_sec"] == closest_value]
    # Also, we remove when there is no start level energy
    df = df.loc[pandas.to_numeric(df["start_level_energy"], errors="coerce").notna()]
    # convert to numeric. Note how one can specify the field by attribute or by string
    keV = g4_units.keV
    df.loc[:, "energy"] = df["energy"].astype(float)
    df.loc[:, "intensity"] = df["intensity"].astype(float)
    return df.energy.to_numpy() * keV, df.intensity.to_numpy() / 100


def isomeric_transition_load_from_iaea_website(a, rad_name):
    # https://nds.iaea.org/relnsd/vcharthtml/VChartHTML.html
    livechart = "https://nds.iaea.org/relnsd/v1/data?"
    nuclide_name = f"{a}{rad_name}"
    url = livechart + f"fields=decay_rads&nuclides={nuclide_name}&rad_types=g"
    try:
        df = lc_read_csv(url)
        # remove x rays lines
        url = livechart + f"fields=decay_rads&nuclides={nuclide_name}&rad_types=x"
        df2 = lc_read_csv(url)
        if not df2.empty:
            # Identify overlapping columns
            overlapping_columns = df.columns.plane_intersection(df2.columns)

            # Convert columns in df2 to the same type as df1
            for col in overlapping_columns:
                df2[col] = df2[col].astype(df[col].dtype)

            df = (
                df.merge(df2, how="outer", indicator=True)
                .loc[lambda x: x["_merge"] == "left_only"]
                .drop("_merge", axis=1)
            )
    except Exception as exception:
        print(exception)
        s = f"Cannot get data for isomeric transition of {rad_name} with this url : {url}"
        warning(s)
        raise Exception(s)
    if "intensity" not in df:
        # when there is no xray
        return None
    return df


def isomeric_transition_load_from_file(filename):
    with open(filename) as infile:
        s = infile.read()
        data = jsonpickle.decode(s)
    return data


def isomeric_transition_extract_from_ion_decay(nuclide, verbose=False):
    # get all channels and gammas for this ion
    g = PhotonIonDecayIsomericTransitionExtractor(nuclide.Z, nuclide.A, verbose=verbose)
    g.extract()
    gammas = g.gammas

    # create the final arrays of energy and weights
    energies = [g.transition_energy for g in gammas]
    weights = [g.final_intensity for g in gammas]

    return energies, weights


def isomeric_transition_load_all_gammas(nuclide, half_life=None):
    daughters = get_nuclide_progeny(nuclide)
    results = []
    if half_life is None:
        sec = g4_units.s
        half_life = nuclide.half_life("s") * sec
    for d in daughters:
        if d.nuclide.nuclide == nuclide.nuclide:
            ene, weights = isomeric_transition_load(d.nuclide, half_life=half_life)
        else:
            ene, weights = isomeric_transition_load(d.nuclide)
        for e, w in zip(ene, weights):
            results.append(
                {
                    "energy": e,
                    "intensity": w,
                    "type": "it",
                    "nuclide": d,
                }
            )
    return results


def isomeric_transition_read_g4_data(z, a, ignore_zero_deex=True):
    # get folder
    data_paths = g4.get_g4_data_paths()
    folder = pathlib.Path(data_paths["G4LEVELGAMMADATA"])
    ion_filename = folder / f"z{z}.a{a}"
    with open(ion_filename) as file:
        lines = [line for line in file]
    levels = Box()
    i = 0
    keV = g4_units.keV
    while i < len(lines) - 1:
        l = Box()
        words = lines[i].split()
        # 1)An integer defining the order index of the level starting by 0  for the ground state
        l.order_level = words[0]
        # 2)A string  defining floating level  (-,+X,+Y,+Z,+U,+V,+W,+R,+S,+T,+A,+B,+C)
        l.floating_level = words[1]
        # 3) Excitation energy of the level (keV)
        l.excitation_energy = float(words[2]) * keV
        # 4) Level half-life (s). A -1 half-life means a stable ground state.
        l.half_life = words[3]
        # 5) JPi information of the level.
        # 6) n_gammas= Number of possible gammas deexcitation channel from the level.
        l.n_gammas = int(words[5])
        # if no channel, we (may) ignore
        if ignore_zero_deex and l.n_gammas == 0:
            i += 1
            continue
        l.daugthers = Box()
        i += 1
        for j in range(0, l.n_gammas):
            a = isomeric_transition_read_one_gamma_deex_channel_line(lines[i])
            l.daugthers[a.daughter_order] = a
            i += 1
        levels[l.order_level] = l
    return levels


def isomeric_transition_read_one_gamma_deex_channel_line(line):
    keV = g4_units.keV
    words = line.split()
    l = Box()
    # 1) The order number of the daughter level.
    l.daughter_order = int(words[0])
    # 2) The energy of the gamma transition.
    l.transition_energy = float(words[1]) * keV
    # 3) The relative gamma emission intensity.
    l.intensity = float(words[2])
    """
    4)The multipolarity number with 1,2,3,4,5,6,7 representing E0,E1,M1,E2,M2,E3,M3  monopole transition
       and  100*Nx+Ny representing multipolarity transition with Ny and Ny taking the value 1,2,3,4,5,6,7
       referring to   E0,E1,M1,E2,M2,E3,M3,.. For example a M1+E2 transition would be written 304.
       A value of 0 means an unknown multipolarity.
    5)The multipolarity mixing ratio. O means that either the transition is a E1,M1,E2,M2 transition
        or the multipolarity mixing ratio is not given in ENSDF.
    6) Total internal conversion coefficient : alpha = Ic/Ig
     Note1: total transition is the sum of gamma de-excitation and internal
          conversion. Therefore total branching ratio is proportional to
          (1+alpha)*Ig
     Note2: total branching ratios from a given level do not always sum up to
          100%. They are re-normalized internally.
     Note3: relative probabilities for gamma de-excitation and internal conversion
          are 1/(1+alpha) and alpha/(1+alpha) respectively
    """
    l.alpha = float(words[5])
    return l


def get_tac_from_decay(ion_name, daughter, start_activity, start_time, end_time, bins):
    """
    The following will be modified according to the TAC:
    ui.start_time, ui.end_time, ui.activity.

    param is ui.tac_from_decay_parameters
    param is a dict with:
    - nuclide: a Nuclide object from radioactivedecay module, with the main ion
    - daughter: the daughter for which we compute the intensity in the time intervals
    - bins: number of bins for the discretised TAC

    - run_timing_intervals: is the list of time range from the Simulation
    """
    ion = rd.Inventory({ion_name: 1.0}, "Bq")
    sec = g4_units.s
    times = np.linspace(start_time, end_time, num=bins, endpoint=True)
    activities = []

    for t in times:
        x = ion.decay(t / sec, "s")
        intensity = x.activities()[daughter.nuclide.nuclide]
        a = intensity * start_activity
        activities.append(a)

    return times, activities


class NumpyArrayHandler(jsonpickle.handlers.BaseHandler):
    def flatten(self, obj, data):
        return obj.tolist()

    def restore(self, obj):
        return np.array(obj)


def gid_build_all_sub_sources(source):
    """
    Build all gamma sources for the given nuclide
    all isomeric transition gammas and all atomic relaxation fluo x-rays
    """

    print("BUILD PHID")
    print("AR = ", source.atomic_relaxation_flag)
    print("IT = ", source.isomeric_transition_flag)

    # consider the user ion
    words = source.particle.split(" ")
    if not source.particle.startswith("ion") or len(words) != 3:
        fatal(
            f"The 'ion' option of user_info must be 'ion Z A', while it is {source.ion}"
        )
    z = int(words[1])
    a = int(words[2])

    if source.isomeric_transition_flag:
        gid_build_all_sub_sources_isomeric_transition(source, z, a)

    if source.atomic_relaxation_flag:
        gid_build_all_sub_sources_atomic_relaxation(
            source, z, a, source.debug_first_daughter_only
        )

    if not source.isomeric_transition_flag and not source.atomic_relaxation_flag:
        fatal(
            f"Error 'isomeric_transition_flag' or 'atomic_relaxation_flag' "
            f"must be True for the source {source.name}"
        )


def gid_build_all_sub_sources_atomic_relaxation(
    ui, z, a, debug_first_daughter_only=False
):
    # get list of decay ions
    id = int(f"{z:3}{a:3}0000")
    first_nuclide = rd.Nuclide(id)
    ui.daughters = get_nuclide_progeny(first_nuclide)
    if debug_first_daughter_only:
        ui.daughters = ui.daughters[:1]
    for daughter in ui.daughters:
        ene, w = atomic_relaxation_load(daughter.nuclide)
        if len(ene) > 0:
            s = gid_build_one_sub_source(
                "atomic_relaxation", ui, daughter, ene, w, first_nuclide
            )
            if s:
                ui.ui_sub_sources.append(s)


def gid_build_all_sub_sources_isomeric_transition(ui, z, a):
    """
    Build (or read from file) all isomeric transition gammas for all daughters in the decay
    """
    # get list of decay ions
    id = int(f"{z:3}{a:3}0000")
    first_nuclide = rd.Nuclide(id)
    ui.daughters = get_nuclide_progeny(first_nuclide)
    ui.log += f"Initial nuclide : {first_nuclide.nuclide}   z={z} a={a}\n"
    ui.log += f"Daughters {len(ui.daughters)}\n\n"

    # loop to add all sources, we copy all options and update the info
    for daughter in ui.daughters:
        ene, w = isomeric_transition_load(daughter.nuclide)
        s = gid_build_one_sub_source(
            "isomeric_transition", ui, daughter, ene, w, first_nuclide
        )
        # some sub sources may be ignored (no gamma)
        if s:
            ui.ui_sub_sources.append(s)


def gid_build_one_sub_source(stype, ui, daughter, ene, w, first_nuclide):
    nuclide = daughter.nuclide
    ion_gamma_daughter = Box({"z": nuclide.Z, "a": nuclide.A})
    ui.log += f"{nuclide.nuclide} {stype} z={nuclide.Z} a={nuclide.A} "
    if len(ene) == 0:
        ui.log += f" no gamma. Ignored\n"
        return None
    ui.log += f" {len(ene)} gammas, with total weights = {np.sum(w) * 100:.2f}%\n"
    # s = copy.deepcopy(ui)
    s = copy.copy(ui)
    s.position = copy.deepcopy(ui.position)
    s.direction = copy.deepcopy(ui.direction)
    s.energy = copy.deepcopy(ui.energy)
    s.ui_sub_sources = None
    s._name = f"{ui.name}_{stype}_{daughter.nuclide.nuclide}"
    # additional info, specific to ion gamma source
    s.particle = "gamma"
    s.energy.type = "spectrum_lines"
    s.energy.ion_gamma_mother = Box({"z": first_nuclide.Z, "a": first_nuclide.A})
    s.energy.ion_gamma_daughter = ion_gamma_daughter
    s.energy.spectrum_weight = w
    s.energy.spectrum_energy = ene
    s.activity = ui.activity
    s.n = ui.n
    # prepare times and activities that will be set during initialisation
    s.tac_from_decay_parameters = {
        "ion_name": first_nuclide,
        "daughter": daughter,
        "bins": ui.tac_bins,
    }
    return s


def isomeric_transition_get_n_greater_energy(nuclide, n):
    ene, w = isomeric_transition_load(nuclide)
    print(ene)
    print(len(ene), len(w))
    if len(ene) == 0:
        return np.array([]), np.array([])
    sorted_indices = np.argsort(w)
    sorted_ene = ene[sorted_indices]
    sorted_w = w[sorted_indices]
    return sorted_ene[-n], sorted_w[-n]
