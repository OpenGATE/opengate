#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import opengate as gate
from opengate.tests import utility
import itk
import numpy as np
import os
from scipy.spatial.transform import Rotation


def main():
    paths = utility.get_default_test_paths(
        __file__, "gate_test042_gauss_gps", "test008"
    )

    # create the simulation
    sim = gate.Simulation()

    # main options
    sim.g4_verbose = False
    sim.g4_verbose_level = 1
    sim.visu = False
    sim.random_seed = 123456
    sim.output_dir = paths.output

    # units
    mm = gate.g4_units.mm
    cm = gate.g4_units.cm

    # add a material database
    sim.volume_manager.add_material_database(paths.gate_data / "HFMaterials2014.db")

    #  change world size
    world = sim.world
    world.size = [600 * cm, 500 * cm, 500 * cm]
    world.material = "Vacuum"

    geometries = ["Box", "Tubs"]
    grid_sizes = [[1, 1, 200], [1, 100, 200], [50, 100, 200]]
    res = 1 * mm
    spacing = [res, res, res]
    box_side = max(max(grid_sizes)) * res

    dose_actors = {}

    i = -10
    for geom in geometries:
        print(f"geom={geom}")
        for grid_size in grid_sizes:
            print(f"  grid_size={grid_size}")
            if geom == "Box":
                size = [s * res for s in grid_size]
            if geom == "Tubs":
                size = [
                    grid_size[0] * res,
                    0,
                    grid_size[2] * res / 2,
                ]  # [rmax, rmin, half_height]

            # mother not rotated, daughter not rotated
            print("    mother not rotated, daughter not rotated")
            transl = [i * box_side + 5 * mm, 0, 0]  # to avoid volume overlapping
            m = my_add_volume(
                sim, "Box", f"mother_{i}", [box_side, box_side, box_side], transl=transl
            )
            v = my_add_volume(
                sim, geom, f"vol_{i}", size, color=[1, 0, 1, 1], mother=m.name
            )
            d = add_dose_actor(sim, f"dose_{i}", grid_size, spacing, v.name)
            dose_actors[
                f"{geom}_{grid_size}_mother_not_rotated_daughter_not_rotated"
            ] = d
            i = i + 1

            # mother not rotated, daughter rotated
            print("    mother not rotated, daughter rotated")
            transl = [i * box_side + 5 * mm, 0, 0]  # to avoid volume overlapping
            m = my_add_volume(
                sim, "Box", f"mother_{i}", [box_side, box_side, box_side], transl=transl
            )
            rot = Rotation.from_euler("y", 90, degrees=True).as_matrix()
            v = my_add_volume(
                sim, geom, f"vol_{i}", size, color=[1, 0, 1, 1], rot=rot, mother=m.name
            )
            d = add_dose_actor(sim, f"dose_{i}", grid_size, spacing, v.name)
            dose_actors[f"{geom}_{grid_size}_mother_not_rotated_daughter_rotated"] = d
            i = i + 1

            # mother rotated, daughter not rotated
            print("    mother rotated, daughter not rotated")
            rot = Rotation.from_euler("y", 90, degrees=True).as_matrix()
            transl = [i * box_side + 5 * mm, 0, 0]  # to avoid volume overlapping
            m = my_add_volume(
                sim,
                "Box",
                f"mother_{i}",
                [box_side, box_side, box_side],
                rot=rot,
                transl=transl,
            )
            v = my_add_volume(
                sim, geom, f"vol_{i}", size, color=[1, 0, 1, 1], mother=m.name
            )
            d = add_dose_actor(sim, f"dose_{i}", grid_size, spacing, v.name)
            dose_actors[f"{geom}_{grid_size}_mother_rotated_daughter_not_rotated"] = d
            i = i + 1

            # mother rotated, daughter rotated
            print("    mother rotated, daughter rotated")
            rot = Rotation.from_euler("y", 90, degrees=True).as_matrix()
            transl = [i * box_side + 5 * mm, 0, 0]  # to avoid volume overlapping
            m = my_add_volume(
                sim,
                "Box",
                f"mother_{i}",
                [box_side, box_side, box_side],
                rot=rot,
                transl=transl,
            )
            rot = Rotation.from_euler("x", 90, degrees=True).as_matrix()
            v = my_add_volume(
                sim, geom, f"vol_{i}", size, color=[1, 0, 1, 1], rot=rot, mother=m.name
            )
            d = add_dose_actor(sim, f"dose_{i}", grid_size, spacing, v.name)
            dose_actors[f"{geom}_{grid_size}_mother_rotated_daughter_rotated"] = d
            i = i + 1

    # start simulation
    sim.run()

    # test
    ok = True
    for test_name, dose in dose_actors.items():
        print(test_name)
        ok = check_dose_grid_geometry(dose.edep.get_output_path(), dose) and ok

    utility.test_ok(ok)


def check_dose_grid_geometry(dose_mhd_path, dose_actor):
    dose_mhd_path = os.path.abspath(dose_mhd_path)
    print(f"Opening image {dose_mhd_path}")
    img = itk.imread(dose_mhd_path)
    data = itk.GetArrayViewFromImage(img)
    shape = data.shape
    spacing = img.GetSpacing()
    shape_ref = tuple(np.flip(dose_actor.size))
    spacing_ref = dose_actor.spacing

    ok = True
    if shape != shape_ref:
        print(f"    shape={shape} not the same as shape_ref{shape_ref}!")
        ok = False
    else:
        print("    Shape ok")

    if spacing != spacing_ref:
        print(f"    spacing={spacing} not the same as spacing_ref={spacing_ref}!")
        ok = False
    else:
        print("    Spacing ok")

    return ok


def my_add_volume(
    sim, geom, name, size, color=[0, 0, 1, 1], rot=None, transl=[0, 0, 0], mother=None
):
    phantom = sim.add_volume(geom, name)
    if mother:
        phantom.mother = mother
    if geom == "Box":
        phantom.size = size
    if geom == "Tubs":
        phantom.rmax = size[0]
        phantom.rmin = size[1]
        phantom.dz = size[2]
    if rot is not None:
        phantom.rotation = rot
    phantom.translation = transl
    phantom.material = "G4_WATER"
    phantom.color = color

    return phantom


def add_dose_actor(sim, name, size, spacing, mother):
    dose = sim.add_actor("DoseActor", name)
    dose.attached_to = mother
    dose.size = size
    dose.spacing = spacing
    dose.hit_type = "random"

    return dose


if __name__ == "__main__":
    main()
