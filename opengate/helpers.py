import colored
import numpy as np
import opengate as gate
import opengate_core as g4
from box import Box
import textwrap
from inspect import getframeinfo, stack
import pkg_resources
import sys
from pathlib import Path
import random
import string
import os
from numpy.random import MT19937
from numpy.random import RandomState, SeedSequence
import inspect
import re
import json

color_error = colored.fg("red") + colored.attr("bold")
color_warning = colored.fg("orange_1")
color_ok = colored.fg("green")


def fatal(s):
    caller = getframeinfo(stack()[1][0])
    ss = f"(in {caller.filename} line {caller.lineno})"
    ss = colored.stylize(ss, color_error)
    gate.log.critical(ss)
    s = colored.stylize(s, color_error)
    gate.log.critical(s)
    sys.exit(-1)


def warning(s):
    s = colored.stylize(s, color_warning)
    gate.log.warning(s)


def raise_except(s):
    s = colored.stylize(s, color_error)
    raise Exception(s)


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


def g4_units(name: str) -> float:
    table = g4.G4UnitDefinition.GetUnitsTable()
    for t in table:
        for a in t.GetUnitsList():
            if a.GetName() == name or a.GetSymbol() == name:
                return a.GetValue()
    units_list = []
    for t in table:
        for a in t.GetUnitsList():
            units_list.append(a.GetSymbol())
    s = [str(u) + " " for u in units_list]
    fatal(f"Error, cannot find the unit named {name}. Known are: {s}")


def g4_best_unit(value, unit_type):
    return g4.G4BestUnit(value, unit_type)


def assert_key(key: str, d: Box):
    if key not in d:
        gate.fatal(f'The key "{key}" is needed in this structure:\n' f"{d}")


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
        gate.fatal(s)


def make_builders(class_names):
    """
    Consider a list of Classname. For each, it build a key/value, with:
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
    resource_path = "/".join(("mac", filename))  # Do not use os.path.join()
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


def check_filename_type(filename):
    # Algorithms (itk) do not support Path -> convert to str
    if isinstance(filename, Path):
        return str(filename)
    return filename


def get_random_folder_name(size=8, create=True):
    r = "".join(random.choices(string.ascii_lowercase + string.digits, k=size))
    r = "run." + r
    if create:
        if not os.path.exists(r):
            print(f"Creating output folder {r}")
            os.mkdir(r)
        if not os.path.isdir(r):
            gate.fatal(f"Error, while creating {r}.")
    return r


def import_gaga_phsp():
    # Try to import torch
    try:
        import torch
    except:
        gate.fatal(
            f'The module "torch" is needed, see https://pytorch.org/get-started/locally/ to install it'
        )

    # Try to import gaga_phsp
    try:
        import gaga_phsp as gaga
    except:
        gate.fatal("The module \"gaga_phsp\" is needed. Use 'pip install gaga_phsp'")

    # Check minimal version of gaga_phsp
    import pkg_resources
    from packaging import version

    gaga_version = pkg_resources.get_distribution("gaga_phsp").version
    gaga_minimal_version = "0.5.8"
    if version.parse(gaga_version) < version.parse(gaga_minimal_version):
        gate.fatal(
            "The minimal version of gaga_phsp is not correct. You should install at least the version "
            + gaga_minimal_version
            + ". Your version is "
            + gaga_version
        )
    return gaga


def import_garf():
    # Try to import torch
    try:
        import torch
    except:
        gate.fatal(
            f'The module "torch" is needed, see https://pytorch.org/get-started/locally/ to install it'
        )

    # Try to import garf_phsp
    try:
        import garf
    except:
        gate.fatal("The module \"garf\" is needed. Use ' pip install garf'")

    # Check minimal version of garf
    import pkg_resources
    from packaging import version

    garf_version = pkg_resources.get_distribution("garf").version
    garf_minimal_version = "2.2"
    if version.parse(garf_version) < version.parse(garf_minimal_version):
        gate.fatal(
            "The minimal version of garf is not correct. You should install at least the version "
            + garf_minimal_version
            + ". Your version is "
            + garf_version
        )
    return garf


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


def print_opengate_info():
    """
    Print information about OpenGate and the environment
    """

    gi = g4.GateInfo
    v = gi.get_G4Version().replace("$Name: ", "")
    v = v.replace("$", "")

    pv = sys.version.replace("\n", "")
    print(f"Python version   {pv}")
    print(f"Platform         {sys.platform}")
    print(f"Site package     {g4.get_site_packages_dir()}")

    print(f"Geant4 version   {v}")
    print(f"Geant4 MT        {gi.get_G4MULTITHREADED()}")
    print(f"Geant4 date      {gi.get_G4Date()}")
    print(f"Geant4 data      {g4.get_G4_data_folder()}")

    print(f"ITK version      {gi.get_ITKVersion()}")

    # Later : gate core lib version
