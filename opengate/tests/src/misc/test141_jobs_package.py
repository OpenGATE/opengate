#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
A campaign folder made by gate.package_simulation (issue #1231):
- copy_inputs=True: the input files (voxel source .mhd + .raw, material
  database) are copied in the campaign folder and simulation.json points to
  these copies; the folder is moved and the original folder hidden, then
  split / run (opengate_jobs, local) / merge work. The job folders link to the
  copies of the campaign (relative links, listed in job_metadata.json), so the
  campaign is moved again after the run and merged there.
- copy_inputs=False: nothing is copied, simulation.json and the job links
  point to the original files.
- sim.run(number_of_jobs=2) without campaign_dir is refused.
"""

import json
import os
import shutil
import subprocess
import sys

import numpy as np
import SimpleITK as sitk

import opengate as gate
from opengate.tests import utility


def opengate_jobs(*args):
    r = subprocess.run(
        [sys.executable, "-m", "opengate.bin.opengate_jobs"] + [str(a) for a in args],
        capture_output=True,
        text=True,
    )
    print(f"opengate_jobs {' '.join(str(a) for a in args)} -> exit {r.returncode}")
    print(r.stdout[-2000:])
    print(r.stderr[-2000:])
    return r


def create_simulation(paths, src):
    """The simulation, built in the folder src (current folder), with its
    input files in src/data."""
    (src / "data").mkdir(parents=True)
    shutil.copy(paths.data / "GateMaterials.db", src / "data")
    image = sitk.GetImageFromArray(np.ones((4, 4, 4), dtype=np.float32))
    image.SetSpacing([5.0, 5.0, 5.0])
    sitk.WriteImage(image, str(src / "data" / "activity.mhd"))

    sim = gate.Simulation()
    sim.output_dir = "output"
    sim.random_seed = 123
    sim.volume_manager.add_material_database("data/GateMaterials.db")
    cm = gate.g4_units.cm
    box = sim.add_volume("Box", "box")
    box.size = [10 * cm, 10 * cm, 10 * cm]
    box.material = "Water"
    source = sim.add_source("VoxelSource", "source")
    source.image = "data/activity.mhd"
    source.particle = "gamma"
    source.energy.mono = 140 * gate.g4_units.keV
    source.activity = 5000 * gate.g4_units.Bq
    stats = sim.add_actor("SimulationStatisticsActor", "stats")
    stats.output_filename = "stats.txt"
    sim.run_timing_intervals = [[0, 1 * gate.g4_units.s]]
    return sim


def read_json(path):
    with open(path) as f:
        return json.load(f)


def json_path(value):
    """A path of simulation.json (str, or Path serialized as its parts)."""
    if isinstance(value, dict):
        return str(os.path.join(*value["__pathlib_path__"]))
    return value


def input_paths(simulation_json):
    d = read_json(simulation_json)
    image = d["source_manager"]["sources"]["source"]["user_info"]["image"]
    database = d["volume_manager"]["material_database_filenames"][0]
    return d, json_path(image), json_path(database)


if __name__ == "__main__":
    paths = utility.get_default_test_paths(__file__, output_folder="test141")
    shutil.rmtree(paths.output, ignore_errors=True)
    src = paths.output / "src"
    src.mkdir(parents=True)
    os.chdir(src)
    sim = create_simulation(paths, src)
    is_ok = True

    # ---------------------------------------------------------------------
    print("\n----- copy_inputs=True")
    campaign = paths.output / "campaign"
    gate.package_simulation(sim, campaign)
    d, image, database = input_paths(campaign / "simulation.json")
    simulation_dir = json_path(d["user_info"]["simulation_dir"])
    files = sorted(p.name for p in campaign.iterdir())
    print(f"files: {files}")
    print(f"simulation_dir: {simulation_dir}, image: {image}, database: {database}")
    b = (
        simulation_dir == "."
        and image == "activity.mhd"
        and database == "GateMaterials.db"
        and files
        == ["GateMaterials.db", "activity.mhd", "activity.raw", "simulation.json"]
    )
    utility.print_test(b, "copy_inputs=True: inputs copied, json points to the copies")
    is_ok = is_ok and b

    # move the campaign, hide the original folder
    moved = paths.output / "moved" / "campaign"
    moved.parent.mkdir()
    shutil.move(campaign, moved)
    hidden = paths.output / "src_hidden"
    os.chdir(paths.output)
    shutil.move(src, hidden)

    r = opengate_jobs("run", moved, "-j", 2, "-l", "--no-merge")
    b = r.returncode == 0
    utility.print_test(b, "moved campaign: split and run without the original folder")
    is_ok = is_ok and b

    job = moved / "job0001"
    metadata = read_json(job / "job_metadata.json")
    links = {
        f: os.readlink(job / f)
        for f in metadata["input_files"]
        if (job / f).is_symlink()
    }
    print(f"job0001 input files: {metadata['input_files']}, links: {links}")
    b = metadata["input_files"] == [
        "GateMaterials.db",
        "activity.mhd",
        "activity.raw",
    ] and all(link == os.path.join("..", f) for f, link in links.items())
    if os.name != "nt":
        b = b and len(links) == 3
    utility.print_test(b, "job folder: relative links to the copies of the campaign")
    is_ok = is_ok and b

    # move the campaign again (after the run), merge there
    moved2 = paths.output / "moved2" / "campaign"
    moved2.parent.mkdir()
    shutil.move(moved, moved2)
    r = opengate_jobs("merge", moved2)
    stats = moved2 / "output" / "stats.txt"
    b = r.returncode == 0 and stats.exists()
    utility.print_test(b, f"campaign moved after the run: merged in {stats}")
    is_ok = is_ok and b

    # ---------------------------------------------------------------------
    print("\n----- copy_inputs=False")
    shutil.move(hidden, src)
    os.chdir(src)
    campaign = paths.output / "campaign_no_copy"
    gate.package_simulation(sim, campaign, copy_inputs=False)
    d, image, database = input_paths(campaign / "simulation.json")
    files = sorted(p.name for p in campaign.iterdir())
    print(f"files: {files}, image: {image}, database: {database}")
    b = (
        files == ["simulation.json"]
        and (campaign / image).resolve() == (src / "data" / "activity.mhd")
        and (campaign / database).resolve() == (src / "data" / "GateMaterials.db")
    )
    utility.print_test(
        b, "copy_inputs=False: nothing copied, json points to the originals"
    )
    is_ok = is_ok and b

    gate.jobs_split(simulation_folder=campaign, number_of_jobs=2)
    link = campaign / "job0002" / "activity.mhd"
    if os.name == "nt":
        # no symbolic link without the Developer Mode: copied
        b = link.exists()
    else:
        b = link.is_symlink() and link.resolve() == (src / "data" / "activity.mhd")
    utility.print_test(b, f"job folder: link to the original file ({link.resolve()})")
    is_ok = is_ok and b

    # ---------------------------------------------------------------------
    print("\n----- sim.run(number_of_jobs=2) without campaign_dir")
    try:
        sim.run(number_of_jobs=2)
        b = False
    except Exception as e:
        print(f"refused: {e}")
        b = "campaign_dir" in str(e)
    utility.print_test(b, "number_of_jobs without campaign_dir refused")
    is_ok = is_ok and b

    utility.test_ok(is_ok)
