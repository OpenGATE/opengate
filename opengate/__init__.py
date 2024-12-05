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


def restart_with_glibc_tunables():
    """
    Restart the current process with GLIBC_TUNABLES set.
    If interactive: we cannot do anything.
    """
    # tunables_value = "glibc.rtld.optional_static_tls=2048000"
    tunables_value = "glibc.rtld.optional_static_tls=2000000"

    def is_python_interactive_shell():
        import __main__

        return not hasattr(__main__, "__file__")

    def print_ld_preload():
        print("Please use the following export lines before importing opengate:")
        print(
            "export LD_LIBRARY_PATH="
            + os.path.join(get_site_packages_dir(), "opengate_core.libs")
            + ":${LD_LIBRARY_PATH}"
        )
        print(
            "export LD_PRELOAD="
            + get_libG4_path("processes")
            + ":"
            + get_libG4_path("geometry")
        )
        print(f"or: \n" f"export GLIBC_TUNABLES=glibc.rtld.optional_static_tls=2000000")

    # Check if the environment variable is already set correctly
    try:
        import opengate_core

        return
    except:
        print("opengate_core cannot be imported...")

    if (
        "site-packages" in pathCurrentFile
    ):  # opengate_core is installed using wheel (for "pip install -e .", the paths are different)
        reloadPython = False
        if (
            "LD_LIBRARY_PATH" not in os.environ
            or os.path.join(get_site_packages_dir(), "opengate_core.libs")
            not in os.environ["LD_LIBRARY_PATH"]
            or "GLIBC_TUNABLES" not in os.environ
        ):
            reloadPython = True
        if (
            "LD_PRELOAD" not in os.environ
            or get_libG4_path("processes") not in os.environ["LD_PRELOAD"]
            or get_libG4_path("geometry") not in os.environ["LD_PRELOAD"]
        ):
            reloadPython = True

        if reloadPython:
            if is_python_interactive_shell():
                try:
                    import opengate_core
                except ImportError as e:
                    print(e)
                    if "cannot allocate memory in static TLS block" in str(e):
                        print_ld_preload()
                return
            print_ld_preload()

            # Set the environment variable
            new_env = os.environ.copy()
            new_env["LD_LIBRARY_PATH"] = (
                os.path.join(get_site_packages_dir(), "opengate_core.libs")
                + new_env["LD_LIBRARY_PATH"]
            )
            new_env["LD_PRELOAD"] = (
                get_libG4_path("processes") + ":" + get_libG4_path("geometry")
            )

            # Restart the process with the new environment
            os.execve(sys.executable, [sys.executable] + sys.argv, new_env)
    else:  # pip install -e . -> we do not know where are libG4
        print(
            f"You installed opengate as developper mode."
            f"Please use the following export line before importing opengate (update it):"
            f"export LD_PRELOAD=<path_to_libG4processes.so>:<path_to_libG4geometry.so>"
            f"or: \n"
            f"export GLIBC_TUNABLES=glibc.rtld.optional_static_tls=2000000"
        )


# Some Python versions distributed by Conda have a buggy `os.add_dll_directory`
# which prevents binary wheels from finding the FFmpeg DLLs in the `av.libs`
# directory. We work around this by adding `av.libs` to the PATH.
if os.name == "nt":
    os.environ["PATH"] = (
        os.path.abspath(
            os.path.join(os.path.dirname(__file__), os.pardir, "opengate_core.libs")
        )
        + os.pathsep
        + os.environ["PATH"]
    )
    os.add_dll_directory(
        os.path.join(os.path.dirname(__file__), os.pardir, "opengate_core.libs")
    )

pathCurrentFile = os.path.abspath(__file__)

if sys.platform.startswith("linux"):
    restart_with_glibc_tunables()
elif sys.platform == "win32":
    print(os.path.dirname(pathCurrentFile))
    os.add_dll_directory(os.path.dirname(pathCurrentFile))

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
