"""Exercise the process-independent core contract of the GATE profiler."""

import json
import time

import opengate as gate
from opengate.profiling import Profiler, profile_method
from opengate.tests import utility


if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, None, "test115")
    paths.output.mkdir(parents=True, exist_ok=True)

    profiler = Profiler(name="campaign")

    # Disabled profilers accept unconditional instrumentation without records.
    with profiler.measure("disabled"):
        pass
    is_ok = utility.print_test(
        len(profiler.to_dictionary()["records"]) == 0,
        "Disabled profiler records no timings",
    )

    class DisabledProbe:
        def __init__(self):
            self.profiler = Profiler()

        @profile_method("execute")
        def execute(self):
            return "executed"

    probe = DisabledProbe()

    def fail_if_measured(*args, **kwargs):
        raise AssertionError("Disabled decorated method entered profiler.measure()")

    probe.profiler.measure = fail_if_measured
    is_ok = (
        utility.print_test(
            probe.execute() == "executed",
            "Disabled decorated methods bypass measurement machinery",
        )
        and is_ok
    )

    profiler.enable()
    split_profiler = profiler.scope("split")
    with split_profiler.measure("prepare"):
        time.sleep(0.001)
    split_profiler.set_value("number_of_jobs", 2)

    # Failed measurements remain visible while preserving the original error.
    try:
        with profiler.measure("failure"):
            raise ValueError("expected")
    except ValueError:
        pass

    snapshot = profiler.to_dictionary()
    paths_by_outcome = {
        record["path"]: record["outcome"] for record in snapshot["records"]
    }
    is_ok = (
        utility.print_test(
            paths_by_outcome["split.prepare"] == "completed",
            "Scoped timing uses its qualified path",
        )
        and is_ok
    )
    is_ok = (
        utility.print_test(
            paths_by_outcome["failure"] == "failed",
            "Failed timing records its outcome",
        )
        and is_ok
    )

    # Snapshot merging is idempotent and JSON round-trips preserve records.
    aggregate = Profiler(name="aggregate", enabled=True)
    aggregate.merge(snapshot, prefix="source")
    aggregate.merge(snapshot, prefix="source")
    profile_path = aggregate.to_json_file(paths.output / "profile.json")
    reloaded = Profiler.from_json_file(profile_path)
    reloaded_snapshot = reloaded.to_dictionary()
    is_ok = (
        utility.print_test(
            len(reloaded_snapshot["records"]) == len(snapshot["records"]),
            "Merging the same snapshot twice is idempotent",
        )
        and is_ok
    )
    is_ok = (
        utility.print_test(
            reloaded_snapshot["values"]["source.split.number_of_jobs"] == 2,
            "Profiler values survive JSON serialization",
        )
        and is_ok
    )
    with profile_path.open(encoding="utf-8") as stream:
        json.load(stream)

    # Simulation objects expose a disabled profiler without serializing it into
    # their configuration dictionary.
    simulation = gate.Simulation()
    is_ok = (
        utility.print_test(
            simulation.profiler.enabled is False,
            "Simulation profiler is disabled by default",
        )
        and is_ok
    )
    is_ok = (
        utility.print_test(
            "profiler" not in simulation.to_dictionary(),
            "Profiler is excluded from simulation configuration serialization",
        )
        and is_ok
    )

    utility.test_ok(is_ok)
