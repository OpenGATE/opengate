#!/usr/bin/env python3
"""Check empty AMF outputs with two workers and few events."""

from opengate.tests import utility
from test103_AMF_threads import run_case


def main():
    """Check empty AMF outputs with two workers and few events."""
    paths = utility.get_default_test_paths(
        __file__, output_folder="test103_AMF_threads_empty"
    )
    run_case(paths.output, 2, no_hit=True, in_process=True, event_count=2)
    utility.test_ok(True)


if __name__ == "__main__":
    main()
