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


def get_libG4_path(lib):
    for element in os.listdir(
        os.path.join(get_site_packages_dir(), "opengate_core.libs")
    ):
        if "libG4" + lib in element:
            return os.path.join(get_site_packages_dir(), "opengate_core.libs", element)


tunables_value = "glibc.rtld.optional_static_tls=2000000"


def print_ld_preload_error(developer_mode=False):
    print("=" * 80)
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
            + get_libG4_path("processes")
            + ":"
            + get_libG4_path("geometry")
        )
    print(f"or: \n" f"export GLIBC_TUNABLES={tunables_value}")
    print("We try to set the variable and restart ...")
    print("=" * 80)
    print("=" * 80)


def is_python_interactive_shell():
    import __main__

    return not hasattr(__main__, "__file__")


def restart_with_qt_libs():
    """
    Restart the current process with QT libs set.
    Only for mac and wheel installation
    """

    if "site-packages" in pathCurrentFile:
        # opengate_core is installed using wheel (for "pip install -e .", the paths are different)
        developer_mode = False
        reload_python = False
        if (
            "DYLD_LIBRARY_PATH" not in os.environ
            or os.path.join(get_site_packages_dir(), "opengate_core/plugins")
            not in os.environ["DYLD_LIBRARY_PATH"]
        ):
            reload_python = True

    else:
        # pip install -e . -> we do not know where are libG4
        developer_mode = True
        reload_python = True

    if reload_python:
        # Set the environment variable
        new_env = os.environ.copy()
        if not developer_mode:
            if "DYLD_LIBRARY_PATH" in new_env:
                new_env["DYLD_LIBRARY_PATH"] = (
                    os.path.join(get_site_packages_dir(), "opengate_core/plugins")
                    + new_env["DYLD_LIBRARY_PATH"]
                )
            else:
                new_env["DYLD_LIBRARY_PATH"] = (
                    os.path.join(get_site_packages_dir(), "opengate_core/plugins")
                )

        # Restart the process with the new environment
        os.execve(sys.executable, [sys.executable] + sys.argv, new_env)


def restart_with_glibc_tunables():
    """
    Restart the current process with GLIBC_TUNABLES set.
    If interactive: we cannot do anything.
    """

    def is_python_interactive_shell():
        import __main__

        return not hasattr(__main__, "__file__")

    # Check if the environment variable is already set correctly
    try:
        import opengate_core

        return
    except:
        pass

    if "site-packages" in pathCurrentFile:
        # opengate_core is installed using wheel (for "pip install -e .", the paths are different)
        developer_mode = False
        reload_python = False
        if (
            "LD_LIBRARY_PATH" not in os.environ
            or os.path.join(get_site_packages_dir(), "opengate_core.libs")
            not in os.environ["LD_LIBRARY_PATH"]
            or "GLIBC_TUNABLES" not in os.environ
        ):
            reload_python = True
        if (
            "LD_PRELOAD" not in os.environ
            or get_libG4_path("processes") not in os.environ["LD_PRELOAD"]
            or get_libG4_path("geometry") not in os.environ["LD_PRELOAD"]
        ):
            reload_python = True

    else:
        # pip install -e . -> we do not know where are libG4
        developer_mode = True
        reload_python = True

    if reload_python:
        if is_python_interactive_shell():
            try:
                import opengate_core
            except ImportError as e:
                print(e)
                if "cannot allocate memory in static TLS block" in str(e):
                    print_ld_preload_error(developer_mode)
            return
        print_ld_preload_error(developer_mode)

        # Set the environment variable
        new_env = os.environ.copy()
        if not developer_mode:
            new_env["LD_LIBRARY_PATH"] = (
                os.path.join(get_site_packages_dir(), "opengate_core.libs")
                + new_env["LD_LIBRARY_PATH"]
            )
            new_env["LD_PRELOAD"] = (
                get_libG4_path("processes") + ":" + get_libG4_path("geometry")
            )
        new_env["GLIBC_TUNABLES"] = tunables_value

        # Restart the process with the new environment
        os.execve(sys.executable, [sys.executable] + sys.argv, new_env)


pathCurrentFile = os.path.abspath(__file__)

if sys.platform.startswith("linux"):
    restart_with_glibc_tunables()
elif sys.platform.startswith("darwin"):
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
