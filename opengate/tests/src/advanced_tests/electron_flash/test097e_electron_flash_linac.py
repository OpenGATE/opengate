import math

import opengate as gate
import opengate.contrib.linacs.electron_flash.electron_flash as fun


def test_geometry_length(_geometry_string):
    sim = gate.Simulation()
    expected_lengths = {
        "ElectronFlash": 316.755,
        "app100": 784.8,
        "app40": 409.8,
        "shaper40": 63.0,
        "mb_40_holes_11": 30.0,
        "mb_40_slit_11": 30.0,
    }
    if _geometry_string == "ElectronFlash":
        total_length = fun.build_ElectronFlash(sim)
    elif _geometry_string == "shaper40":
        total_length, (_, _, _, _) = fun.build_passive_collimation(
            sim, _geometry_string, center_z=53
        )
    elif _geometry_string in ("mb_40_holes_11", "mb_40_slit_11"):
        total_length = fun.build_passive_collimation(sim, _geometry_string, center_z=25)
    else:
        total_length = fun.build_passive_collimation(sim, _geometry_string)
    expected = expected_lengths.get(_geometry_string)
    assert expected is not None, f"Unknown geometry: {_geometry_string}"
    assert math.isclose(
        total_length, expected, rel_tol=1e-5
    ), f"Length mismatch for {_geometry_string}: expected {expected}, got {total_length}"


test_geometry_length("ElectronFlash")
test_geometry_length("app100")
test_geometry_length("app40")
test_geometry_length("shaper40")
test_geometry_length("mb_40_holes_11")
test_geometry_length("mb_40_slit_11")
