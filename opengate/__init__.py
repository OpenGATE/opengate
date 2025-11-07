import os
import sys
import site


def get_site_packages_dir():
    site_package = [p for p in site.getsitepackages() if "site-packages" in p]
    if len(site_package) > 0:
        site_package = site_package[0]
    else:
        site_package = site.getusersitepackages()
    return site_package


def get_lib_g4_path(lib):
    for element in os.listdir(
        os.path.join(get_site_packages_dir(), "opengate_core.libs")
    ):
        if "libG4" + lib in element:
            return os.path.join(get_site_packages_dir(), "opengate_core.libs", element)


tunables_value = "glibc.rtld.optional_static_tls=2000000"


def print_ld_preload_error(developer_mode=False):
    print("=" * 80)
    print("The opengate_core library cannot be loaded.")
    print("Error is: cannot allocate memory in static TLS block")
    print("Please use the following export lines before importing opengate:")
    print(
        "export LD_LIBRARY_PATH="
        + os.path.join(get_site_packages_dir(), "opengate_core.libs")
        + ":${LD_LIBRARY_PATH}"
    )
    if developer_mode:
        print(
            "export LD_PRELOAD=<path_to_libG4processes.so>:<path_to_libG4processes.so>:${LD_LIBRARY_PATH}"
        )
    else:
        print(
            "export LD_PRELOAD="
            + get_lib_g4_path("processes")
            + ":"
            + get_lib_g4_path("geometry")
        )
    print(f"or: \n" f"export GLIBC_TUNABLES={tunables_value}")
    print("=" * 80)
    print()


def is_python_interactive_shell():
    import __main__

    return not hasattr(__main__, "__file__")


def is_developer_installation():
    path_current_file = os.path.abspath(__file__)
    if "site-packages" in path_current_file:
        return False
    return True


def restart_with_qt_libs():
    """
    Restart the current process with QT libs set.
    Only for mac and wheel installation
    """
    developer_mode = is_developer_installation()
    if is_python_interactive_shell() or developer_mode:
        # we cannot know the real plugin_path nor if DYLD_LIBRARY_PATH is already correctly set
        # so we ignore.
        # no vizualisation
        return

    plugin_path = os.path.join(get_site_packages_dir(), "opengate_core/plugins")

    # do nothing if the plugin_path is already in the env
    if (
        "DYLD_LIBRARY_PATH" in os.environ
        and plugin_path in os.environ["DYLD_LIBRARY_PATH"]
    ):
        return

    # Otherwise, we set the env and try to restart the script
    new_env = os.environ.copy()
    if "DYLD_LIBRARY_PATH" in new_env:
        new_env["DYLD_LIBRARY_PATH"] = plugin_path + new_env["DYLD_LIBRARY_PATH"]
    else:
        new_env["DYLD_LIBRARY_PATH"] = plugin_path

    # Restart the process with the new environment
    # print(new_env["DYLD_LIBRARY_PATH"])
    os.execve(sys.executable, [sys.executable] + sys.argv, new_env)


def check_ld_preload(e):
    """
    Check if the LD_PRELOAD environment variable is set correctly.
    """

    # Check if opengate_core can be loaded, if yes we continue
    if "cannot allocate memory in static TLS block" not in str(e):
        print("Cannot import opengate_core module")
        print(e)
        exit(-1)

    developer_mode = is_developer_installation()

    # We can do nothing if this is an interactive shell
    if is_python_interactive_shell():
        print_ld_preload_error(developer_mode)
        exit(-1)

    # print error message
    if developer_mode:
        print_ld_preload_error(developer_mode)
        exit(-1)


try:
    import opengate_core
except ImportError as e:
    if sys.platform.startswith("linux"):
        check_ld_preload(e)

if sys.platform.startswith("darwin"):
    restart_with_qt_libs()

# subpackages
import opengate.sources
import opengate.geometry
import opengate.geometry.materials
import opengate.geometry.solids
import opengate.geometry.utility
import opengate.geometry.volumes
import opengate.actors
import opengate.contrib

# modules directly under /opengate/
import opengate.managers
import opengate.utility
import opengate.logger
import opengate.exception
import opengate.runtiming
import opengate.definitions
import opengate.userhooks
import opengate.image
import opengate.physics
import opengate.base
import opengate.engines

# import opengate.postprocessors

# These objects are imported at the top level of the package
# because users will frequently use them
from opengate.managers import Simulation
from opengate.managers import create_sim_from_json
from opengate.utility import g4_units
from opengate.base import help_on_user_info
