#!/usr/bin/env python3
"""Check a single event and serial lifecycle guards."""

from opengate.tests import utility
from test103_AMF_threads import run_case


def main():
    """Check a single event and serial lifecycle guards."""
    paths = utility.get_default_test_paths(__file__, output_folder="test103_AMF_threads_serial")
    run_case(paths.output, 1, in_process=True, event_count=1)
    utility.test_ok(True)


if __name__ == "__main__":
    main()
