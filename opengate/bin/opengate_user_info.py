#!/usr/bin/env python3

import click
from opengate.userinfo import UserInfo
from opengate.geometry.builders import volume_type_names
from opengate.sources.builders import source_type_names

CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])


def print_one(v, the_type):
    n = len(v.type_name)
    print(f'{v.type_name} {"-" * (50 - n)}')
    user_info = UserInfo(the_type, v.type_name, "fake")
    for element in user_info.__dict__:
        val = str(user_info.__dict__[element])
        val = val.replace("\n", "")
        print(f"    {element:<25}     {val}")


@click.command(context_settings=CONTEXT_SETTINGS)
def go():
    """
    Print information about all available user parameters
    """

    print()
    print(f"Volumes")
    print()
    for v in volume_type_names:
        print_one(v, "Volume")

    print()
    print(f"Sources")
    print()
    for v in source_type_names:
        print_one(v, "Source")

    print()
    print(f"Actors")
    print()
    for v in actor_type_names:
        print_one(v, "Actor")


if __name__ == "__main__":
    go()
