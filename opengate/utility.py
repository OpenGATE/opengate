import numpy as np
import scipy as sc
from numpy.random import MT19937
from numpy.random import RandomState, SeedSequence
import random
from box import Box
import textwrap
import inspect
import importlib.resources as resources
import sys
from pathlib import Path
import string
import os
import re
import json
import importlib
import importlib.util
from importlib.metadata import version
import shutil

import opengate_core as g4
from opengate import get_site_packages_dir
from .exception import fatal, warning


class LazyModuleLoader:
    """
    Lazy loading allows you to delay the loading of a module until it's actually needed.
    This can be useful if a module is expensive to load or if it may not be used in
    every execution of the program.
    We use it for some modules that was found to delay the startup time, in particular:
    - radioactivedecay and pandas in phidsources
    - torch and gaga in gansources (only required for some features)
    """

    def __init__(self, module_name):
        self.module_name = module_name
        self.module = None

    def __getattr__(self, name):
        if self.module is None:
            # Check module existence and import it
            try:
                # print(f"LazyModuleLoader is importing module {self.module_name} ...")
                self.module = importlib.import_module(self.module_name)
                # print("... done")
            except ModuleNotFoundError:
                fatal(
                    f"The module '{self.module_name}' is not installed. "
                    f"Please install it before proceeding."
                )
        return getattr(self.module, name)


git = LazyModuleLoader("git")


def assert_equal_dic(d1, d2, name=""):
    for k in d1:
        if k not in d2:
            fatal(f"ERROR missing key {k} in {name}")
        if isinstance(d1[k], np.ndarray):
            if np.any(d2[k] != d1[k]):
                fatal(f"ERROR np array {k} {d1[k]} in {name}")
        else:
            if d2[k] != d1[k]:
                fatal(f"ERROR value for {k} in {name}")
    for k in d2:
        if k not in d1:
            fatal(f"ERROR, additional key {k} in {name}")


def ensure_directory_exists(directory):
    p = Path(directory)
    p.mkdir(parents=True, exist_ok=True)


def delete_folder_contents(folder_path):
    if os.path.exists(folder_path):
        for filename in os.listdir(folder_path):
            file_path = os.path.join(folder_path, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            except Exception as e:
                warning(f"Failed to delete {file_path}. Reason: {e}")


# units were previously loaded dynamically from G4
# g4_units = Box()
# for t in g4.G4UnitDefinition.GetUnitsTable():
#     for a in t.GetUnitsList():
#         g4_units[str(a.GetName())] = a.GetValue()
#         g4_units[str(a.GetSymbol())] = a.GetValue()

# This dictionary was created with devtools.print_g4units_dict_string()
# It should be updated if Geant4 (ever) changes the units.
# It is hard-coded, as opposed to the dynamic variant above,
# because the build process on readthedocs cannot call G4 functions
g4_units = Box(
    {
        "parsec": 3.0856775807e19,
        "pc": 3.0856775807e19,
        "kilometer": 1000000.0,
        "km": 1000000.0,
        "meter": 1000.0,
        "m": 1000.0,
        "centimeter": 10.0,
        "cm": 10.0,
        "millimeter": 1.0,
        "mm": 1.0,
        "micrometer": 0.001,
        "um": 0.001,
        "nanometer": 1.0000000000000002e-06,
        "nm": 1.0000000000000002e-06,
        "angstrom": 1.0000000000000001e-07,
        "Ang": 1.0000000000000001e-07,
        "fermi": 1e-12,
        "fm": 1e-12,
        "kilometer2": 1000000000000.0,
        "km2": 1000000000000.0,
        "meter2": 1000000.0,
        "m2": 1000000.0,
        "centimeter2": 100.0,
        "cm2": 100.0,
        "millimeter2": 1.0,
        "mm2": 1.0,
        "barn": 9.999999999999999e-23,
        "millibarn": 9.999999999999999e-26,
        "mbarn": 9.999999999999999e-26,
        "microbarn": 9.999999999999999e-29,
        "mubarn": 9.999999999999999e-29,
        "nanobarn": 1e-31,
        "nbarn": 1e-31,
        "picobarn": 1e-34,
        "pbarn": 1e-34,
        "kilometer3": 1e18,
        "km3": 1e18,
        "meter3": 1000000000.0,
        "m3": 1000000000.0,
        "centimeter3": 1000.0,
        "cm3": 1000.0,
        "millimeter3": 1.0,
        "mm3": 1.0,
        "liter": 1000000.0,
        "L": 1000000.0,
        "dL": 100000.0,
        "cL": 10000.0,
        "mL": 1000.0,
        "radian": 1.0,
        "rad": 1.0,
        "milliradian": 0.001,
        "mrad": 0.001,
        "degree": 0.017453292519943295,
        "deg": 0.017453292519943295,
        "steradian": 1.0,
        "sr": 1.0,
        "millisteradian": 0.001,
        "msr": 0.001,
        "second": 1000000000.0,
        "s": 1000000000.0,
        "millisecond": 1000000.0,
        "ms": 1000000.0,
        "microsecond": 1000.0,
        "us": 1000.0,
        "nanosecond": 1.0,
        "ns": 1.0,
        "picosecond": 0.001,
        "ps": 0.001,
        "minute": 60000000000.0,
        "min": 60000000000.0,
        "hour": 3600000000000.0,
        "h": 3600000000000.0,
        "day": 86400000000000.0,
        "d": 86400000000000.0,
        "year": 3.1536e16,
        "y": 3.1536e16,
        "hertz": 1e-09,
        "Hz": 1e-09,
        "kilohertz": 1.0000000000000002e-06,
        "kHz": 1.0000000000000002e-06,
        "megahertz": 0.001,
        "MHz": 0.001,
        "cm/ns": 10.0,
        "mm/ns": 1.0,
        "cm/us": 0.01,
        "km/s": 0.001,
        "cm/ms": 1e-05,
        "m/s": 1e-06,
        "cm/s": 1e-08,
        "mm/s": 1e-09,
        "eplus": 1.0,
        "e+": 1.0,
        "coulomb": 6.241509074460763e18,
        "C": 6.241509074460763e18,
        "electronvolt": 1e-06,
        "eV": 1e-06,
        "kiloelectronvolt": 0.001,
        "keV": 0.001,
        "megaelectronvolt": 1.0,
        "MeV": 1.0,
        "gigaelectronvolt": 1000.0,
        "GeV": 1000.0,
        "teraelectronvolt": 1000000.0,
        "TeV": 1000000.0,
        "petaelectronvolt": 1000000000.0,
        "PeV": 1000000000.0,
        "millielectronVolt": 1e-09,
        "meV": 1e-09,
        "joule": 6241509074460.763,
        "J": 6241509074460.763,
        "eV/c": 1e-06,
        "keV/c": 0.001,
        "MeV/c": 1.0,
        "GeV/c": 1000.0,
        "TeV/c": 1000000.0,
        "GeV/cm": 100.0,
        "MeV/cm": 0.1,
        "keV/cm": 0.0001,
        "eV/cm": 1e-07,
        "milligram": 6.241509074460762e18,
        "mg": 6.241509074460762e18,
        "gram": 6.241509074460762e21,
        "g": 6.241509074460762e21,
        "kilogram": 6.241509074460762e24,
        "kg": 6.241509074460762e24,
        "g/cm3": 6.241509074460762e18,
        "mg/cm3": 6241509074460762.0,
        "kg/m3": 6241509074460762.0,
        "g/cm2": 6.241509074460761e19,
        "mg/cm2": 6.2415090744607624e16,
        "kg/cm2": 6.2415090744607614e22,
        "cm2/g": 1.6021766340000004e-20,
        "eV*cm2/g": 1.6021766340000002e-26,
        " eV*cm2/g": 1.6021766340000002e-26,
        "keV*cm2/g": 1.6021766340000002e-23,
        "MeV*cm2/g": 1.6021766340000004e-20,
        "GeV*cm2/g": 1.6021766340000003e-17,
        "watt": 6241.509074460762,
        "W": 6241.509074460762,
        "newton": 6241509074.460763,
        "N": 6241509074.460763,
        "pascal": 6241.509074460763,
        "Pa": 6241.509074460763,
        "bar": 624150907.4460763,
        "atmosphere": 632420906.9697368,
        "atm": 632420906.9697368,
        "ampere": 6241509074.460763,
        "A": 6241509074.460763,
        "milliampere": 6241509.0744607635,
        "mA": 6241509.0744607635,
        "microampere": 6241.509074460762,
        "muA": 6241.509074460762,
        "nanoampere": 6.2415090744607635,
        "nA": 6.2415090744607635,
        "volt": 1e-06,
        "V": 1e-06,
        "kilovolt": 0.001,
        "kV": 0.001,
        "megavolt": 1.0,
        "MV": 1.0,
        "volt/m": 9.999999999999999e-10,
        "V/m": 9.999999999999999e-10,
        "kilovolt/m": 1e-06,
        "kV/m": 1e-06,
        "megavolt/m": 0.001,
        "MV/m": 0.001,
        "weber": 1000.0,
        "Wb": 1000.0,
        "tesla": 0.001,
        "T": 0.001,
        "kilogauss": 0.0001,
        "kG": 0.0001,
        "gauss": 1.0000000000000001e-07,
        "G": 1.0000000000000001e-07,
        "kelvin": 1.0,
        "K": 1.0,
        "mole": 1.0,
        "mol": 1.0,
        "g/mole": 6.241509074460762e21,
        "g/mol": 6.241509074460762e21,
        "becquerel": 1e-09,
        "Bq": 1e-09,
        "curie": 37.0,
        "Ci": 37.0,
        "gray": 1.0000000000000002e-12,
        "Gy": 1.0000000000000002e-12,
    }
)


# def g4_units(name: str) -> float:
#     table = g4.G4UnitDefinition.GetUnitsTable()
#     for t in table:
#         for a in t.GetUnitsList():
#             if a.GetName() == name or a.GetSymbol() == name:
#                 return a.GetValue()
#     units_list = []
#     for t in table:
#         for a in t.GetUnitsList():
#             units_list.append(a.GetSymbol())
#     s = [str(u) + " " for u in units_list]
#     fatal(f"Error, cannot find the unit named {name}. Known are: {s}")
def get_material_name_variants(material_name):
    """Get different variants of a material name, e.g. with/without prepended G4_, only first letter capital.
    Intended to bridge inconsistencies in naming conventions.
    """
    # ensure the input is string, not G4String
    material_name = str(material_name)
    variants = [
        material_name,
        material_name.lstrip("G4_"),
        material_name.lstrip("G4_").capitalize(),
    ]
    return list(set(variants))


def g4_best_unit(value, unit_type):
    return g4.G4BestUnit(value, unit_type)


def g4_best_unit_tuple(value, unit_type):
    bu = g4.G4BestUnit(value, unit_type)
    parts = str(bu).split(" ", 1)
    float_part = float(parts[0])
    unit_part = parts[1].strip()
    return float_part, unit_part


def assert_key(key: str, d: Box):
    if key not in d:
        fatal(f'The key "{key}" is needed in this structure:\n' f"{d}")


def assert_keys(keys: list, d: Box):
    for key in keys:
        assert_key(key, d)


def indent(amount, text, ch=" "):
    """
    Prefix the text with indent spaces
    https://stackoverflow.com/questions/8234274/how-to-indent-the-contents-of-a-multi-line-string
    """
    return textwrap.indent(text, amount * ch)


def assert_unique_element_name(elements, name):
    if name in elements:
        s = (
            f"Error, cannot add '{name}' because this element's name already exists"
            f" in: {elements}."
        )
        fatal(s)


def make_builders(class_names):
    """
    Consider a list of Classname. For each, it builds a key/value, with:
    - the type of the class as key
    - and a lambda function that create an object of this class as value
    """
    builder_list = {}
    for c in class_names:
        # note the following lambda:
        # https://stackoverflow.com/questions/2295290/what-do-lambda-function-closures-capture
        try:
            builder_list[c.type_name] = lambda x, y=c: y(x)
        except AttributeError:
            # if type_name is not an attribute of the class,
            # we use the name of the class as key.
            # Also: no name parameter (this is for Physics List)
            builder_list[c.__name__] = lambda y=c: y()
    return builder_list


def read_mac_file_to_commands(filename):
    # read a file located into the 'mac' folder of the source code
    # return a list of commands
    resource_package = __package__
    with resources.open_text(f"{resource_package}.mac", filename) as f:
        c = f.read()
        commands = []
        for s in c.split("\n"):
            if s == "":
                continue
            # if s[0] == '#':
            #    continue
            commands.append(s)
        return commands


def ensure_filename_is_str(filename):
    # Some software packages, e.g. itk, do not support Path -> convert to str
    if isinstance(filename, Path):
        return str(filename)
    elif filename is None:
        return ""
    else:
        return filename


def insert_suffix_before_extension(file_path, suffix, suffix_separator="-"):
    path = Path(file_path)
    if not suffix:
        return path

    suffix = suffix.strip("_- *").lower()
    # Handle filenames with nested extensions e.g. '.nii.gz'
    if path.name.endswith(".nii.gz"):
        stem = path.name[: -len(".nii.gz")]
        new_path = path.with_name(f"{stem}{suffix_separator}{suffix}.nii.gz")
    else:
        new_path = path.with_name(f"{path.stem}{suffix_separator}{suffix}{path.suffix}")

    return new_path


def get_random_folder_name(size=8, create=True):
    r = "".join(random.choices(string.ascii_lowercase + string.digits, k=size))
    r = "run." + r
    directory = Path(r)
    if create:
        if not directory.exists():
            print(f"Creating output folder {r}")
            directory.mkdir(parents=True, exist_ok=True)
        if not directory.is_dir():
            fatal(f"Error, while creating {r}.")
    return r


def get_rnd_seed(seed):
    return RandomState(MT19937(SeedSequence(seed)))


def print_dic(dic):
    print(json.dumps(dic, indent=4, default=str))


def get_release_date(opengate_version):
    import requests

    package_name = "opengate"
    url = f"https://pypi.org/pypi/{package_name}/json"
    response = requests.get(url)

    if response.status_code == 200:
        package_data = response.json()
        releases = package_data["releases"]
        if releases:
            # latest_version = max(releases, key=lambda v: package_data['releases'][v][0]['upload_time'])
            release_date = package_data["releases"][opengate_version][0]["upload_time"]
            return f"{release_date}"
        else:
            return "unknown"
    else:
        return "unknown"


def get_gate_folder():
    module_path = os.path.dirname(__file__)
    return Path(module_path)


def get_data_folder():
    return get_gate_folder() / "data"


def get_tests_folder():
    return get_gate_folder() / "tests" / "src"


def get_library_path():
    folder_base = (get_gate_folder() / "..").resolve()

    subpaths = [Path("opengate_core"), Path("core") / "opengate_core"]
    path = None

    for subpath in subpaths:
        try_path = folder_base / subpath
        if os.path.exists(try_path):
            path = try_path
            break

    if not path:
        return "unknown"

    files = os.listdir(path)
    lib_ext = "pyd" if os.name == "nt" else "so"
    libs = [file for file in files if file.endswith(f".{lib_ext}")]
    if len(libs) == 0:
        return "unknown"
    elif len(libs) > 1:
        return f"unknown: multiple .{lib_ext} files in {path} ({libs})"

    return path / libs[0]


def get_contrib_path():
    module_path = os.path.dirname(__file__)
    return Path(module_path) / "contrib"


def print_opengate_info():
    """
    Print information about OpenGate and the environment
    """

    gi = g4.GateInfo
    v = gi.get_G4Version().replace("$Name: ", "")
    v = v.replace("$", "")
    module_path = get_gate_folder()

    pv = sys.version.replace("\n", "")
    print(f"Python version   {pv}")
    print(f"Platform         {sys.platform}")
    print(f"Site package     {get_site_packages_dir()}")

    print(f"Geant4 version   {v}")
    print(f"Geant4 MT        {gi.get_G4MULTITHREADED()}")
    print(f"Geant4 Qt        {gi.get_G4VIS_USE_OPENGLQT()} {gi.get_QT_VERSION()}")
    print(f"Geant4 GDML      {gi.get_G4GDML()}")
    print(f"Geant4 date      {gi.get_G4Date().replace(')', '').replace('(', '')}")
    print(f"Geant4 data      {g4.get_g4_data_folder()}")

    print(f"ITK version      {gi.get_ITKVersion()}")

    print(f"GATE version     {version('opengate')}")
    print(f"GATE folder      {module_path}")
    print(f"GATE data        {get_data_folder()}")
    print(f"GATE tests       {get_tests_folder()}")
    print(f"GATE core path   {get_library_path()}")

    # check if from a git version ?
    git_path = Path(module_path).parent
    try:
        git_repo = git.Repo(git_path)
        sha = git_repo.head.object.hexsha
        print(f"GATE git sha     {sha}")
        commit = git_repo.head.commit
        commit_date = commit.committed_datetime
        print(f"GATE date        {commit_date}  (last commit)")

    except:
        print(f"GATE date        {get_release_date(version('opengate'))} (pypi)")


def calculate_variance(value_array, squared_value_array, number_of_samples):
    return np.clip(
        (
            squared_value_array / number_of_samples
            - np.power(value_array / number_of_samples, 2)
        )
        / (number_of_samples - 1),
        0,
        None,
    )


def standard_error_c4_correction(n):
    """
    Parameters
    ----------
    n : integer
        Number of subsets (of the samples).

    Returns
    -------
    c4 : double
        Factor to convert the biased standard error of the mean of subsets of the sample into an unbiased
        -  assuming a normal distribution .
        Usage: standard_error(unbiased) = standard_deviation_of_mean(=biased) / c4
        The reason is that the standard deviation of the mean of subsets of the sample X underestimates the true standard error. For n = 2 this underestimation is about 25%.

        Values for c4: n=2: 0.7979; n= 9: 0.9693

    """
    return (
        np.sqrt(2 / (n - 1)) * sc.special.gamma(n / 2) / sc.special.gamma((n - 1) / 2)
    )


def read_json_file(filename: Path) -> dict:
    """
    Read a JSON file into a Python dictionary.

    :param filename: Path object
        The filename of the JSON file to read.
    :return: dict
        The data from the JSON file.
    """
    if not filename.is_file():
        fatal(f"File {filename} does not exist.")

    with open(filename, "rb") as f:
        return json.load(f)


def get_basename_and_extension(filename):
    """Return the basename and extension of a filename even if .nii.gz is used."""
    base = filename
    extensions = []
    while os.path.splitext(base)[1]:
        base, ext = os.path.splitext(base)
        extensions.append(ext)
    extensions.reverse()
    return os.path.basename(base), "".join(extensions)
