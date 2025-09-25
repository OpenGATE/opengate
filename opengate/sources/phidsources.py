from ..exception import fatal, warning
from ..utility import g4_units, LazyModuleLoader
from .generic import GenericSource
import opengate_core as g4

from box import Box
import jsonpickle
import numpy as np
import pathlib
import urllib
import copy
import os
import inspect
from ..base import process_cls

# the following packages seems to take a bit of time to load
rd = LazyModuleLoader("radioactivedecay")
pandas = LazyModuleLoader("pandas")


class PhotonFromIonDecaySource(GenericSource):
    """
    Manage a set of GenericSource sub_sources, one for each nuclide gamma lines, for all daughters of the given ion.
    Each sub_sources will have:
    - activity managed by a TAC, corresponding to the Bateman equation during the time range
    - spectrum energy line for isomeric transition
    - spectrum energy line for atomic relaxation (fluo)
    - particle forced to gammas
    """

    # hints for IDE
    verbose: bool
    tac_bins: float
    dump_log: str
    atomic_relaxation_flag: bool
    isomeric_transition_flag: bool

    user_info_defaults = {
        "verbose": (False, {"doc": "Verbose for debug"}),
        "tac_bins": (200, {"doc": "Number of bins for the TAC"}),
        "dump_log": (None, {"doc": "write log in the given filename"}),
        "atomic_relaxation_flag": (
            True,
            {"doc": "Consider gammas from atomic relaxation"},
        ),
        "isomeric_transition_flag": (
            True,
            {"doc": "Consider gammas from isomeric transition"},
        ),
    }

    def __init__(self, *args, **kwargs):
        super().__init__(self, *args, **kwargs)
        # list of all sub_sources
        self.sub_sources = []
        # False if this is the main first source
        self.is_a_sub_source = False

        # used during sub_sources creation
        self.tac_from_decay_parameters = None
        # used during sub_sources creation
        self.daughters = None

        # debug
        self.log = ""
        self.debug_first_daughter_only = False

    def __initcpp__(self):
        g4.GateGenericSource.__init__(self)

    def initialize(self, run_timing_intervals):
        if not self.is_a_sub_source:
            # this is called only one single time to build the list of sub_sources
            if (g4.IsMultithreadedApplication() and g4.G4GetThreadId() == -1) or (
                not g4.IsMultithreadedApplication()
            ):
                phid_build_all_sub_sources(self)

        # super class conventional initialization

        GenericSource.initialize(self, run_timing_intervals)
        self.initialize_start_end_time(run_timing_intervals)
        for sub_source in self.sub_sources:

            sub_source.start_time = self.start_time
            sub_source.end_time = self.end_time

        # this will initialize and set user_info to the cpp side
        # for all sub_sources
        for sub_source in self.sub_sources:
            # get tac from decay
            p = Box(sub_source.tac_from_decay_parameters)
            sub_source.tac_times, sub_source.tac_activities = get_tac_from_decay(
                p.ion_name,
                p.daughter,
                sub_source.activity,
                sub_source.start_time,
                sub_source.end_time,
                p.bins,
            )
            # update the tac
            update_sub_source_tac_activity(sub_source)

            # check
            self.check_ui_activity(sub_source)
            self.check_confine(sub_source)

            # final initialize to cpp side
            # sub_source.n = np.array([sub_source.n],dtype = int)
            sub_source.InitializeUserInfo(sub_source.user_info)

        # dump log
        if self.user_info.dump_log is not None:
            with open(self.user_info.dump_log, "w") as outfile:
                outfile.write(self.log)

    def add_to_source_manager(self, source_manager):
        for g4_source in self.sub_sources:
            source_manager.AddSource(g4_source)


def update_sub_source_tac_activity(sub_source):
    if sub_source.tac_times is None and sub_source.tac_activities is None:
        return
    n = len(sub_source.tac_times)
    if n != len(sub_source.tac_activities):
        fatal(
            f"option tac_activities must have the same size than tac_times in source '{sub_source.name}'"
        )

    # scale the activity if energy_spectrum is given (because total may not be 100%)
    total = sum(sub_source.energy.spectrum_weights)
    sec = g4_units.s
    Bq = g4_units.Bq

    # it is important to set the starting time for this source as the tac
    # may start later than the simulation timing
    i = 0
    while i < len(sub_source.tac_activities) and sub_source.tac_activities[i] <= 0:
        i += 1
    if i >= len(sub_source.tac_activities):
        # gate.warning(f"Source '{sub_source.name}' TAC with zero activity.")
        sub_source.start_time = sub_source.end_time + 1 * sec
    else:
        sub_source.start_time = sub_source.tac_times[i]
        # IMPORTANT : activities must be x by total here
        # (not before, because it can be called several times in MT mode)
        sub_source.SetTAC(
            sub_source.tac_times, np.array(sub_source.tac_activities) * total
        )

    if sub_source.verbose:
        print(
            f"GammaFromIon source {sub_source.name}    total = {total * 100:8.2f}%   "
            f" gammas lines = {len(sub_source.energy.spectrum_weights)}   "
            f" total activity = {sum(sub_source.tac_activities) / Bq:10.3f}"
            f" first activity = {sub_source.tac_activities[0] / Bq:5.2f}"
            f" last activity = {sub_source.tac_activities[-1] / Bq:5.2f}"
        )


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
            overlapping_columns = df.columns.plane_intersection_torch(df2.columns)

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


def phid_build_all_sub_sources(source):
    """
    Build all gamma sources for the given nuclide
    all isomeric transition gammas and all atomic relaxation fluo x-rays
    """

    # consider the user ion
    words = source.particle.split(" ")
    if not source.particle.startswith("ion") or len(words) != 3:
        fatal(
            f"The 'ion' option of user_info must be 'ion Z A', while it is {source.ion}"
        )
    z = int(words[1])
    a = int(words[2])

    if source.isomeric_transition_flag:
        phid_build_all_sub_sources_isomeric_transition(source, z, a)

    if source.atomic_relaxation_flag:
        phid_build_all_sub_sources_atomic_relaxation(
            source, z, a, source.debug_first_daughter_only
        )

    if not source.isomeric_transition_flag and not source.atomic_relaxation_flag:
        fatal(
            f"Error 'isomeric_transition_flag' or 'atomic_relaxation_flag' "
            f"must be True for the source {source.name}"
        )


def phid_build_all_sub_sources_atomic_relaxation(
    source, z, a, debug_first_daughter_only=False
):
    # get list of decay ions
    id = int(f"{z:3}{a:3}0000")
    first_nuclide = rd.Nuclide(id)
    source.daughters = get_nuclide_progeny(first_nuclide)
    if debug_first_daughter_only:
        source.daughters = source.daughters[:1]
    for daughter in source.daughters:
        ene, w = atomic_relaxation_load(daughter.nuclide)
        if len(ene) > 0:
            s = phid_build_one_sub_source(
                "atomic_relaxation", source, daughter, ene, w, first_nuclide
            )
            if s:
                source.sub_sources.append(s)


def phid_build_all_sub_sources_isomeric_transition(source, z, a):
    """
    Build (or read from file) all isomeric transition gammas for all daughters in the decay
    """
    # get list of decay ions
    id = int(f"{z:3}{a:3}0000")
    first_nuclide = rd.Nuclide(id)
    source.daughters = get_nuclide_progeny(first_nuclide)
    source.log += f"Initial nuclide : {first_nuclide.nuclide}   z={z} a={a}\n"
    source.log += f"Daughters {len(source.daughters)}\n\n"

    # loop to add all sources, we copy all options and update the info
    for daughter in source.daughters:
        ene, w = isomeric_transition_load(daughter.nuclide)
        s = phid_build_one_sub_source(
            "isomeric_transition", source, daughter, ene, w, first_nuclide
        )
        # some sub sources may be ignored (no gamma)
        if s:
            source.sub_sources.append(s)


def phid_build_one_sub_source(stype, source, daughter, ene, w, first_nuclide):
    nuclide = daughter.nuclide
    ion_gamma_daughter = Box({"z": nuclide.Z, "a": nuclide.A})
    source.log += f"{nuclide.nuclide} {stype} z={nuclide.Z} a={nuclide.A} "
    if len(ene) == 0:
        source.log += f" no gamma. Ignored\n"
        return None
    source.log += f" {len(ene)} gammas, with total weights = {np.sum(w) * 100:.2f}%\n"
    name = f"{source.name}__{stype}_of_{daughter.nuclide.nuclide}"
    s = PhotonFromIonDecaySource(name=name)
    s.is_a_sub_source = True
    s.sub_sources = []
    s.position = copy.deepcopy(source.position)
    s.direction = copy.deepcopy(source.direction)
    s.energy = copy.deepcopy(source.energy)
    s.verbose = source.verbose
    s.particle = "gamma"
    s.energy.type = "spectrum_discrete"
    s.energy.ion_gamma_mother = Box({"z": first_nuclide.Z, "a": first_nuclide.A})
    s.energy.ion_gamma_daughter = ion_gamma_daughter
    s.energy.spectrum_weights = w
    s.energy.spectrum_energies = ene
    s.activity = source.activity
    s.n = source.n

    # prepare times and activities that will be set during initialisation
    s.tac_from_decay_parameters = {
        "ion_name": first_nuclide,
        "daughter": daughter,
        "bins": source.tac_bins,
    }

    return s


process_cls(PhotonFromIonDecaySource)
