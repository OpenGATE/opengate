import numpy as np
import scipy as sc
from numpy.random import MT19937
from numpy.random import RandomState, SeedSequence
import random
from box import Box
import textwrap
import inspect
import pkg_resources
import sys
from pathlib import Path
import string
import os
import re
import json
import importlib
import importlib.util
from importlib.metadata import version

import opengate_core as g4
from .exception import fatal


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
        if not k in d2:
            fatal(f"ERROR missing key {k} in {name}")
        if isinstance(d1[k], np.ndarray):
            if np.any(d2[k] != d1[k]):
                fatal(f"ERROR np array {k} {d1[k]} in {name}")
        else:
            if d2[k] != d1[k]:
                fatal(f"ERROR value for {k} in {name}")
    for k in d2:
        if not k in d1:
            fatal(f"ERROR, additional key {k} in {name}")


def ensure_directory_exists(directory):
    p = Path(directory)
    p.mkdir(parents=True, exist_ok=True)


g4_units = Box()
for t in g4.G4UnitDefinition.GetUnitsTable():
    for a in t.GetUnitsList():
        g4_units[str(a.GetName())] = a.GetValue()
        g4_units[str(a.GetSymbol())] = a.GetValue()


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
    resource_package = __name__
    resource_path = "/".join(("mac", filename))  # Do not use os.filename.join()
    template = pkg_resources.resource_string(resource_package, resource_path)
    c = template.decode("utf-8")
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
        if not directory.isdir():
            fatal(f"Error, while creating {r}.")
    return r


def get_rnd_seed(seed):
    return RandomState(MT19937(SeedSequence(seed)))


def DDF():
    """
    Debug print current Function name
    """
    print("--> Entering", inspect.stack()[1][3])


def DD(arg):
    """
    Debug print variable name and its value
    """
    frame = inspect.currentframe()
    try:
        context = inspect.getframeinfo(frame.f_back).code_context
        caller_lines = "".join([line.strip() for line in context])
        m = re.search(r"DD\s*\((.+?)\);*$", caller_lines)
        if m:
            caller_lines = m.group(1)
            # end if
        print(caller_lines, "=", arg)
    finally:
        del frame


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
    print(f"Site package     {g4.get_site_packages_dir()}")

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
