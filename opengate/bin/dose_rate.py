#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import copy
import json
import pathlib
import sys
import click
from box import Box
from opengate.contrib.dose.doserate import create_simulation, merge_vrt_dose_rate

CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])


@click.command(context_settings=CONTEXT_SETTINGS)
@click.argument(
    "json_param", type=click.Path(exists=True), required=False, default=None
)
@click.option(
    "--mode",
    "-m",
    type=click.Choice(
        ["vrt", "analog", "e-", "gamma_tle", "gamma"], case_sensitive=False
    ),
    default=None,
    help="Simulation mode: vrt (runs e- and gamma_tle then merges), analog (full ion decay), e-, gamma_tle, gamma (default: from JSON or 'vrt')",
)
@click.option(
    "--activity",
    "-a",
    default=None,
    type=float,
    help="Total simulated activity in Bq (overrides JSON). In vrt mode, this applies to gamma.",
)
@click.option(
    "--radionuclide",
    "-r",
    default=None,
    type=str,
    help="Radionuclide name (e.g. Lu177, Y90, Ac225) or ion 'Z A' (e.g. '89 225') (overrides JSON).",
)
@click.option(
    "--e-factor",
    default=None,
    type=float,
    help="In vrt mode, factor by which electron activity is reduced (default: from JSON or 10.0).",
)
@click.option(
    "--threads",
    "-t",
    default=None,
    type=int,
    help="Number of threads (default: from JSON or 4, 1 on Windows).",
)
@click.option(
    "--output_folder",
    "-o",
    default=None,
    type=click.Path(),
    help="Output folder. Default is auto-named based on mode (e.g. output_vrt, output_analog, output_e, output_gamma_tle).",
)
@click.option(
    "--visu",
    is_flag=True,
    default=False,
    help="Enable visualization (forces single thread).",
)
@click.option(
    "--merge-only",
    nargs=2,
    type=click.Path(exists=True),
    default=None,
    metavar="DIR_E DIR_GAMMA",
    help="Merge precomputed electron and gamma simulation folders and exit.",
)
def go(
    json_param,
    mode,
    activity,
    radionuclide,
    e_factor,
    threads,
    output_folder,
    visu,
    merge_only,
):
    # Handle merge-only mode first
    if merge_only:
        dir_e, dir_gamma = merge_only
        out_dir = (
            pathlib.Path(output_folder)
            if output_folder
            else pathlib.Path("output_merged")
        )
        ef = e_factor if e_factor is not None else 10.0
        print(
            f"Merging VRT dose rate outputs from {dir_e} and {dir_gamma} into {out_dir} (e_factor={ef})..."
        )
        merged = merge_vrt_dose_rate(dir_e, dir_gamma, out_dir, e_factor=ef)
        print(f"Merged {len(merged)} image(s):")
        for f in merged:
            print(f"  {f}")
        return

    if not json_param:
        click.echo(
            "Error: Missing argument 'JSON_PARAM'. Use --help for usage instructions.",
            err=True,
        )
        sys.exit(1)

    # Open the parameter file
    json_path = pathlib.Path(json_param).resolve()
    try:
        with open(json_path, "r") as f:
            param_dict = json.load(f)
    except IOError:
        click.echo(f"Cannot open input json file {json_param}", err=True)
        sys.exit(1)

    param = Box(param_dict)

    # Resolve relative paths in JSON relative to json file directory if not found in cwd
    json_dir = json_path.parent
    for key in ["ct_image", "table_mat", "table_density", "activity_image"]:
        if hasattr(param, key) and param[key]:
            p = pathlib.Path(param[key])
            if not p.exists() and (json_dir / p).exists():
                param[key] = str((json_dir / p).resolve())

    # Apply overrides from CLI
    if radionuclide is not None:
        param.radionuclide = radionuclide

    if activity is not None:
        param.activity_bq = activity
    elif not hasattr(param, "activity_bq") or param.activity_bq is None:
        param.activity_bq = 1e6
    param.activity_bq = int(float(param.activity_bq))

    default_threads = 1 if sys.platform.startswith("win") else 4
    if threads is not None:
        param.number_of_threads = threads
    elif not hasattr(param, "number_of_threads") or param.number_of_threads is None:
        param.number_of_threads = default_threads

    if visu:
        param.visu = True
    elif not hasattr(param, "visu"):
        param.visu = False

    if e_factor is not None:
        param.e_factor = e_factor
    elif "e_factor" in param and param.e_factor is not None:
        param.e_factor = float(param.e_factor)
    elif "e-factor" in param and param["e-factor"] is not None:
        param.e_factor = float(param["e-factor"])
    else:
        param.e_factor = 10.0
    e_factor = float(param.e_factor)

    if not hasattr(param, "verbose"):
        param.verbose = True
    if not hasattr(param, "density_tolerance_gcm3"):
        param.density_tolerance_gcm3 = 0.05

    # Determine if radionuclide is an alpha emitter or generic ion 'Z A' (incompatible with VRT)
    is_non_vrt_rad = False
    if hasattr(param, "radionuclide"):
        rad_val = param.radionuclide
        if isinstance(rad_val, (list, tuple)):
            is_non_vrt_rad = True
        elif isinstance(rad_val, str):
            rad_str = rad_val.strip()
            if rad_str in ["Ac225", "Ra223", "Bi213", "Pb212"]:
                is_non_vrt_rad = True
            elif rad_str.startswith("ion") or (
                len(rad_str.split()) > 1 and rad_str.split()[0].isdigit()
            ):
                is_non_vrt_rad = True

    # Determine mode: CLI takes precedence, then JSON, then default
    if mode is None:
        if hasattr(param, "mode") and param.mode:
            mode = param.mode
        elif is_non_vrt_rad:
            mode = "analog"
        else:
            mode = "vrt"
    if mode == "":
        mode = "analog"

    if mode == "vrt" and is_non_vrt_rad:
        click.echo(
            f"Error: VRT mode is designed for beta/gamma emitters (e.g. Lu177, Y90). "
            f"For '{param.radionuclide}', please use --mode analog.",
            err=True,
        )
        sys.exit(1)

    # Determine output folder
    if output_folder:
        out_dir = pathlib.Path(output_folder)
    elif (
        hasattr(param, "output_folder")
        and param.output_folder
        and param.output_folder != "AUTO"
    ):
        out_dir = pathlib.Path(param.output_folder)
    else:
        out_dir = pathlib.Path(f"output_{mode}")

    # Mode: VRT (automated pipeline)
    if mode == "vrt":
        print(f"=== Running VRT Dose Rate Simulation ===")
        print(f"Target activity (gamma): {param.activity_bq:.2e} Bq")
        act_e = int(float(param.activity_bq) / e_factor)
        print(f"Electron activity (e_factor={e_factor}): {act_e:.2e} Bq")
        print(f"Output directory: {out_dir}")

        out_e = out_dir / "e"
        out_gamma = out_dir / "gamma_tle"
        out_e.mkdir(parents=True, exist_ok=True)
        out_gamma.mkdir(parents=True, exist_ok=True)

        # 1. Run electrons
        print("\n--- Step 1/2: Simulating electrons (e-) ---")
        param_e = copy.deepcopy(param)
        param_e.mode = "e-"
        param_e.activity_bq = act_e
        param_e.output_folder = str(out_e)
        sim_e = create_simulation(param_e)
        sim_e.run(start_new_process=True)
        stats_e = sim_e.get_actor("Stats")
        if stats_e:
            print(stats_e)

        # 2. Run photons with TLE
        print("\n--- Step 2/2: Simulating photons (gamma_tle) ---")
        param_gamma = copy.deepcopy(param)
        param_gamma.mode = "gamma_tle"
        param_gamma.activity_bq = param.activity_bq
        param_gamma.output_folder = str(out_gamma)
        sim_gamma = create_simulation(param_gamma)
        sim_gamma.run(start_new_process=True)
        stats_gamma = sim_gamma.get_actor("Stats")
        if stats_gamma:
            print(stats_gamma)

        # 3. Merge
        print(f"\n--- Merging VRT outputs into {out_dir} (e_factor={e_factor}) ---")
        merged = merge_vrt_dose_rate(out_e, out_gamma, out_dir, e_factor=e_factor)
        print(f"Merged {len(merged)} image(s):")
        for f in merged:
            print(f"  {f}")
        print(f"\nDone. VRT results saved in: {out_dir}")

    else:
        # Single simulation mode: analog, e-, gamma_tle, gamma
        mode_map = {
            "analog": "",
            "e-": "e-",
            "gamma_tle": "gamma_tle",
            "gamma": "gamma",
        }
        param.mode = mode_map[mode]
        out_dir.mkdir(parents=True, exist_ok=True)
        param.output_folder = str(out_dir)

        print(f"=== Running Dose Rate Simulation (mode={mode}) ===")
        print(f"Simulated activity: {param.activity_bq:.2e} Bq")
        print(f"Output directory: {out_dir}")

        sim = create_simulation(param)
        sim.run(start_new_process=True)

        stats = sim.get_actor("Stats")
        if stats:
            print(stats)
        print(f"\nDone. Results saved in: {out_dir}")


# --------------------------------------------------------------------------
if __name__ == "__main__":
    go()
