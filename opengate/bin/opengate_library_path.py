#!/usr/bin/env python3

import site
import os
import click
from pathlib import Path


def return_site_packages_dir() -> Path:
    site_package = [p for p in site.getsitepackages() if "site-packages" in p][0]
    return Path(site_package)


def get_site_packages_dir():
    print(str(return_site_packages_dir()))


def get_libG4processes_path():
    lib_path = return_site_packages_dir() / "opengate_core.libs"
    for element in lib_path.iterdir():
        if "libG4processes" in element.name:
            print(str(element))


def get_libG4geometry_path():
    lib_path = return_site_packages_dir() / "opengate_core.libs"
    for element in lib_path.iterdir():
        if "libG4geometry" in element.name:
            print(str(element))


# -----------------------------------------------------------------------------
CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])


@click.command(context_settings=CONTEXT_SETTINGS)
@click.option("--path", "-p", default="", help="Path", required=True)
def go(path):
    """
    Tool to have the path of folders
    """
    if path == "libG4processes":
        get_libG4processes_path()
    elif path == "libG4geometry":
        get_libG4geometry_path()
    elif path == "site_packages":
        get_site_packages_dir()


# -----------------------------------------------------------------------------
if __name__ == "__main__":
    go()
