# This file handles the way opengate is imported.
import os
import sys


def restart_with_glibc_tunables():
    """
    Restart the current process with GLIBC_TUNABLES set.
    """
    # tunables_value = "glibc.rtld.optional_static_tls=2048000"
    tunables_value = "glibc.rtld.optional_static_tls=1500000"

    # Check if the environment variable is already set correctly
    if os.environ.get("GLIBC_TUNABLES") != tunables_value:
        # Set the environment variable
        new_env = os.environ.copy()
        new_env["GLIBC_TUNABLES"] = tunables_value

        # Restart the process with the new environment
        os.execve(sys.executable, [sys.executable] + sys.argv, new_env)

        # Exit the current process
        sys.exit()


if sys.platform.startswith("linux"):
    restart_with_glibc_tunables()
