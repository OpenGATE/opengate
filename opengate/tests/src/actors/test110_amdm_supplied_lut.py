#!/usr/bin/env python3
"""Supplied-table acceptance, checked against independently recorded transport steps."""
from pathlib import Path
import hashlib
import numpy as np
import uproot
import opengate as gate
from opengate.tests import utility
from test110_amdm_helpers import output_dir, make_sim, arrays, check_outputs

LUT_SHA256 = "93d42113b9f48e3ec069000f5983e4568f7bca2e873d1cb06186d08f949771ab"


if __name__ == "__main__":
    lut = Path(__file__).resolve().parent / "fixtures" / "test110_amdm" / "AMDM_LUT.txt"
    assert lut.is_file(), f"AMDM acceptance requires its development LUT fixture: {lut}"
    checksum = hashlib.sha256(lut.read_bytes()).hexdigest()
    assert checksum == LUT_SHA256, checksum
    table = np.loadtxt(lut)
    assert table.shape == (4000, 22)
    assert (table[:, 0] == 8).sum() == 401 and (table[:, 0] == 9).sum() == 399
    directory = output_dir("supplied_lut")
    sim, actor = make_sim(directory, lut=lut, primaries=40)
    actor.AMDM_Bins = 10
    actor.InitializeUserInfo(actor.user_info)
    for charge in range(1, 11):
        group = table[table[:, 0] == charge]
        queries = [0.0, group[0, 1], (group[0, 1] + group[1, 1]) / 2,
                   group[-1, 1], group[-1, 1] + 100]
        for energy in queries:
            expected_lookup = [np.interp(energy, group[:, 1], group[:, c])
                               for c in range(2, 22)]
            np.testing.assert_allclose(actor.Lookup(charge, energy), expected_lookup,
                                       rtol=1e-13, atol=1e-13)
    # Public PhaseSpaceActor records every step independently of AMDM scoring.
    audit = sim.add_actor("PhaseSpaceActor", "steps")
    audit.attached_to = "phantom"
    audit.steps_to_store = "all"
    audit.attributes = ["PDGCode", "PostKineticEnergy", "PreKineticEnergy",
                        "TotalEnergyDeposit", "Weight"]
    audit.output_filename = "steps.root"
    sim.run(start_new_process=True)
    steps = uproot.open(audit.get_output_path())["steps"].arrays(library="numpy")
    # This low-energy EM-only carbon case has no nuclear fragmentation. Verify
    # the assertion rather than assuming the transport had no other ion species.
    code = steps["PDGCode"]
    mask = code == 1000060120  # carbon-12, charge 6, baryon number 12
    positive = (code > 1_000_000_000) | (code == 2212) | (code == -11)
    assert mask.any() and np.all(code[positive] == 1000060120), np.unique(code)
    energies = steps["PostKineticEnergy"][mask] / 12.0
    weights = steps["TotalEnergyDeposit"][mask] * steps["Weight"][mask]
    assert weights.sum() > 0 and np.ptp(energies) > 1, "must exercise energy-dependent lookup"
    group = table[table[:, 0] == 6]
    expected = np.column_stack([np.interp(energies, group[:, 1], group[:, c])
                                for c in range(2, 22)])
    expected_delta = (expected[:, 10:] * weights[:, None]).sum(axis=0)
    expected_gamma = (expected[:, :10] * expected[:, 10:] * weights[:, None]).sum(axis=0)
    energy, raw_delta, raw_gamma, delta, gamma = arrays(actor)
    # Independent step recording, unit conversion and np.interp oracle: allow
    # only floating-point summation order error, not Monte Carlo disagreement.
    np.testing.assert_allclose(energy.sum(), weights.sum(), rtol=1e-11, atol=1e-8)
    np.testing.assert_allclose(raw_delta.sum(axis=(1, 2, 3)), expected_delta, rtol=1e-11, atol=1e-8)
    np.testing.assert_allclose(raw_gamma.sum(axis=(1, 2, 3)), expected_gamma, rtol=1e-11, atol=1e-8)
    scored = energy > 0
    np.testing.assert_allclose(delta[:, scored].sum(axis=0), 1., rtol=0, atol=1e-12)
    assert np.all(delta >= 0) and np.all(delta <= 1 + 1e-12)
    assert np.all(gamma >= 0) and np.isfinite(gamma).all()
    assert np.all(delta[:, ~scored] == 0) and np.all(gamma[:, ~scored] == 0)
    check_outputs(sim, actor, samples=40)
    print("Supplied LUT", lut, checksum)
    print("Recorded carbon steps", mask.sum(), "restricted MeV", energy.sum())
    print("Independent np.interp/transport-step oracle passed for all ten raw bins")
    utility.test_ok(True)
