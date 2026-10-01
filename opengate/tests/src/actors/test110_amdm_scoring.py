#!/usr/bin/env python3
"""Analytical bin scoring, public configuration, geometry and output contract."""

import itk
import numpy as np
import opengate as gate
from opengate.exception import GateDeprecationError
from opengate.tests import utility
from test110_amdm_helpers import (
    GAMMA,
    DELTA,
    constant_lut,
    arrays,
    output_dir,
    make_sim,
    assert_constant_scoring,
    check_outputs,
)

if __name__ == "__main__":
    scored = []
    for coordinate, hit, raw, weight in [
        ("local", "pre", True, 1.0),
        ("global", "post", False, 2.0),
        (None, "middle", True, 1.0),
        ("global", "random", True, 1.0),
    ]:
        directory = output_dir(f"scoring_{coordinate}_{hit}")
        sim, actor = make_sim(
            directory, coordinate=coordinate, hit_type=hit, weight=weight
        )
        actor.storeMergingData = raw
        sim.run(start_new_process=True)
        total = assert_constant_scoring(actor)
        check_outputs(sim, actor, samples=80)
        scored.append(total)
        assert (
            actor.user_output.amdm.merged_data.get_data_item_object(0).number_of_samples
            == 80
        )
    # The same seeded fully-contained beam gives linear scaling with track weight.
    # Hit position cannot change its total deposit in a grid covering the target.
    np.testing.assert_allclose(scored[1], 2 * scored[0], rtol=1e-12, atol=1e-9)
    sim, actor = make_sim(
        output_dir("image_coordinates"),
        coordinate="attached_to_image",
        image_volume=True,
    )
    sim.run(start_new_process=True)
    assert_constant_scoring(actor)
    check_outputs(sim, actor, samples=80)
    for invalid, value, message in [
        ("AMDM_Bins", 0, "positive integer"),
        ("AMDM_Bins", 2.5, "positive integer"),
        ("AMDM_Bins", True, "positive integer"),
        ("size", [2, 0, 2], "positive integers"),
        ("size", [2, 2.5, 2], "positive integers"),
        ("spacing", [1, -1, 1], "greater than zero"),
        ("translation", [0, float("nan"), 0], "finite"),
        ("rotation", np.zeros((3, 3)), "orthonormal"),
        ("LUTfilename", "", "nonempty"),
    ]:
        sim, actor = make_sim(output_dir("invalid"))
        setattr(actor, invalid, value)
        try:
            actor.initialize()
        except Exception as error:
            assert message in str(error), (invalid, error)
        else:
            raise AssertionError(f"accepted invalid {invalid}={value}")
    sim, actor = make_sim(output_dir("invalid"))
    try:
        actor.hit_type = "unknown"
    except Exception as error:
        assert "hit_type" in str(error)
    else:
        raise AssertionError("accepted unknown hit_type")
    try:
        actor.output = "old.mhd"
    except GateDeprecationError:
        pass
    else:
        raise AssertionError("obsolete output must use current deprecation behavior")
    # Missing charge: initialization succeeds, but accepted energy and all bins are zero.
    sim, actor = make_sim(output_dir("missing_charge"), particle="ion 8 16")
    sim.run(start_new_process=True)
    for array in arrays(actor):
        assert np.all(array == 0)
    check_outputs(sim, actor, samples=80)
    for particle in ["gamma", "e-"]:
        directory = output_dir("excluded_" + particle)
        lut = constant_lut(directory, {1: (GAMMA, DELTA)})
        sim, actor = make_sim(directory, lut=lut, particle=particle)
        sim.source_manager.sources["ions"].energy.mono = 0.5
        sim.run(start_new_process=True)
        for array in arrays(actor):
            assert np.all(array == 0)
    # Preserve the legacy zero-baryon positive-charge rule explicitly: every
    # positron query uses its charge's upper endpoint, not its finite kinetic energy.
    directory = output_dir("positron_compatibility")
    lut = directory / "positron_lut.txt"
    lut.write_text("1 1 2 7 13 .25 .75 0\n1 10 5 11 17 .25 .75 0\n")
    sim, actor = make_sim(directory, lut=lut, particle="e+")
    sim.source_manager.sources["ions"].energy.mono = 0.5
    sim.run(start_new_process=True)
    assert_constant_scoring(actor, gamma=[5, 11, 17])
    # Disk controls do not disable the internal denominators needed by derived views.
    sim, actor = make_sim(output_dir("no_disk"))
    actor.write_to_disk = False
    actor.storeMergingData = True
    sim.run(start_new_process=True)
    assert_constant_scoring(actor)
    assert not list(sim.output_dir.glob("*.mhd"))
    print(
        "Analytical scoring, zero denominators, metadata and configuration checks passed"
    )
    utility.test_ok(True)
