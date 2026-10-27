#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Test 136: outputs of all the voxel deposit actors (issue #993), with
2 threads, 2 runs (data kept per run) and a merge of 2 split jobs.

For each actor (one child process per actor, option --child):
1. 2 threads, 2 runs: the merged image is the sum of the run images (for
   the quotient images LET, RE, alpha/beta mix: the numerator and the
   denominator); the run images are not modified by the merge
2. 2 jobs + merge: the merged image is the sum of the job images (for the
   quotient images: the quotient of the summed numerators and denominators);
   for RBEActor, the RBE images are computed again after the merge
"""

import subprocess
import sys
from pathlib import Path

import itk
import numpy as np

import opengate as gate
from opengate.tests import utility

cm, mm, MeV, sec = (
    gate.g4_units.cm,
    gate.g4_units.mm,
    gate.g4_units.MeV,
    gate.g4_units.s,
)

# actor type -> (output name, is a quotient image)
ACTORS = {
    "DoseActor": ("edep_with_uncertainty", False),
    "TLEDoseActor": ("edep_with_uncertainty", False),
    "ProductionAndStoppingActor": ("production_stopping", False),
    "FluenceActor": ("counts_with_uncertainty", False),
    "LETActor": ("let", True),
    "REActor": ("RE_mix", True),
    "RBEActor": ("alpha_mix", True),
}


def build(actor_type, output_dir, ref_path):
    sim = gate.Simulation()
    sim.number_of_threads = 2
    sim.random_seed = 123654
    sim.output_dir = output_dir
    sim.verbose_level = "NONE"
    # electromagnetic physics only: enough here, and fast to initialize
    sim.physics_manager.physics_list_name = "G4EmStandardPhysics_option4"

    box = sim.add_volume("Box", "box")
    box.size = [10 * cm] * 3
    box.material = "G4_WATER"

    src = sim.add_source("GenericSource", "source")
    src.position.type = "disc"
    src.position.radius = 5 * mm
    src.position.translation = [0, 0, -6 * cm]
    src.direction.type = "momentum"
    src.direction.momentum = [0, 0, 1]
    if actor_type in ("REActor", "RBEActor"):
        src.particle = "ion 6 12"
        src.energy.mono = 1200 * MeV
        src.number_of_primaries = [20, 30]
    elif actor_type == "TLEDoseActor":
        src.particle = "gamma"
        src.energy.mono = 1 * MeV
        src.number_of_primaries = [300, 500]
    else:
        src.particle = "proton"
        src.energy.mono = 80 * MeV
        src.number_of_primaries = [200, 300]
    sim.run_timing_intervals = [[0, 1 * sec], [1 * sec, 2 * sec]]

    a = sim.add_actor(actor_type, "a")
    a.attached_to = box
    a.size = [5, 5, 10]
    a.spacing = [2 * cm, 2 * cm, 1 * cm]
    if actor_type == "FluenceActor":
        # the scoring by process uses a helper actor (also in MT)
        a.score_by_process = True
    if actor_type == "REActor":
        a.model = "RE"
        a.score_in = "G4_WATER"
        a.lookup_table_path = ref_path / "RE_Alanine_RBEstyle.txt"
    if actor_type == "RBEActor":
        a.hit_type = "random"
        a.model = "mMKM"
        a.r_nucleus = 3.9
        a.energy_per_nucleon = False
        a.lookup_table_path = ref_path / "mkm_nirs_LQparameters_SURVIVAL.csv"
    name, _ = ACTORS[actor_type]
    a.user_output[name].keep_data_per_run = True
    return sim, a


def image_sum(data_item):
    return float(itk.array_from_image(data_item.data).sum())


def read(path):
    return itk.array_from_image(itk.imread(str(path))).astype(float)


def run_child(actor_type, base, ref_path):
    name, quotient = ACTORS[actor_type]
    items = (0, 1) if quotient else (0,)
    if actor_type == "RBEActor":
        # with mMKM, the merged alpha numerator is modified at the end of the
        # simulation (from the numerator and the denominator): only the
        # denominator (edep) is the sum of the runs
        items = (1,)

    # 1. 2 threads, 2 runs
    sim, a = build(actor_type, base / "mt", ref_path)
    sim.run(start_new_process=False)
    u = a.user_output[name]
    for i in items:
        r0 = image_sum(u.data_per_run[0].data[i])
        r1 = image_sum(u.data_per_run[1].data[i])
        m = image_sum(u.merged_data.data[i])
        b = np.isclose(m, r0 + r1, rtol=1e-6) and m > 0
        print(f"RESULT runs item {i}: {b} merged {m:.6g} = {r0:.6g} + {r1:.6g}")

    # 2. 2 jobs + merge
    sim, a = build(actor_type, base / "jobs", ref_path)
    campaign = base / "campaign"
    sim.run(
        number_of_jobs=2,
        wait_for_result=True,
        merge_after_run=True,
        campaign_dir=campaign,
    )
    u = a.user_output[name]
    job_outputs = [campaign / f"job{j:04d}" / "output" for j in (1, 2)]
    if quotient:
        # quotient of the summed numerators and denominators
        num = den = 0
        for o in job_outputs:
            num = num + read(o / u.get_output_path(which="merged", item=0).name)
            den = den + read(o / u.get_output_path(which="merged", item=1).name)
        expected = np.where(den != 0, num / np.where(den != 0, den, 1), 0)
        merged = read(
            base / "jobs" / u.get_output_path(which="merged", item="quotient").name
        )
    else:
        expected = sum(
            read(o / u.get_output_path(which="merged", item=0).name)
            for o in job_outputs
        )
        merged = read(base / "jobs" / u.get_output_path(which="merged", item=0).name)
    b = np.allclose(merged, expected, rtol=1e-5, atol=1e-12) and merged.sum() > 0
    print(f"RESULT jobs merge: {b} (sum {merged.sum():.6g})")
    if actor_type == "RBEActor":
        b = (base / "jobs" / a.rbe.get_output_path().name).is_file() and (
            base / "jobs" / a.rbe_dose.get_output_path().name
        ).is_file()
        print(f"RESULT jobs RBE images computed after the merge: {b}")


if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, None, "test136")
    ref_path = paths.output_ref.parent / "test087"

    if "--child" in sys.argv:
        run_child(sys.argv[-2], Path(sys.argv[-1]), ref_path)
        sys.exit(0)

    is_ok = True
    for actor_type in ACTORS:
        base = paths.output / actor_type
        r = subprocess.run(
            [sys.executable, __file__, "--child", actor_type, str(base)],
            capture_output=True,
            text=True,
        )
        results = [l for l in r.stdout.splitlines() if l.startswith("RESULT")]
        b = r.returncode == 0 and len(results) > 0
        b = b and all(": True" in l for l in results)
        if not b:
            print(r.stdout[-3000:])
            print(r.stderr[-3000:])
        for l in results:
            print(f"   {actor_type} {l[7:]}")
        is_ok = utility.print_test(b, f"{actor_type}") and is_ok

    utility.test_ok(is_ok)
