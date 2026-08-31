#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import click
from opengate_core import g4DataSetup

CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])


@click.command(context_settings=CONTEXT_SETTINGS)
@click.option(
    "--optional_data", "-o", is_flag=True, help="Download the optional data of G4"
)
def go(
    optional_data,
):
    """
    Download the G4 data. If the option -o is set, the optional G4 data are also downloaded
    """
    g4DataSetup.check_g4_data()
    if optional_data:
        missing_data = g4DataSetup.get_missing_g4_optional_data()
        g4DataSetup.download_g4_optional_data(missing_data)
    print("Done!")


if __name__ == "__main__":
    go()
