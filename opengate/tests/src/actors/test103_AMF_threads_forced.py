#!/usr/bin/env python3
"""Check forced multithread mode with a single worker."""

from opengate.tests import utility
from test103_AMF_threads import run_case


def main():
    """Check forced multithread mode with a single worker."""
    paths = utility.get_default_test_paths(
        __file__, output_folder="test103_AMF_threads_forced"
    )
    run_case(paths.output, 1, forced=True, in_process=True, event_count=4)
    utility.test_ok(True)


if __name__ == "__main__":
    main()
