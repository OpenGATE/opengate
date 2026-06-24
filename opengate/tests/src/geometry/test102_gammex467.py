import opengate as gate
from opengate.contrib.phantoms import gammex467
from opengate.tests import utility
from opengate.voxelize import voxelize_geometry, write_voxelized_geometry

import itk
import numpy as np
import filecmp

# Define the units used in the simulation set-up
cm = gate.g4_units.cm
mm = gate.g4_units.mm

if __name__ == "__main__":
    # create the simulation
    sim = gate.Simulation()

    paths = utility.get_default_test_paths(__file__, "", "test102_gammex467")

    # Change world size
    world = sim.world
    world.size = [100. * cm, 100. * cm, 100. * cm]

    # Add the Gammex 467 phantom
    gammex467_phantom = gammex467.add_gammex467_phantom(sim)

    volume_labels, image = voxelize_geometry(
        sim, extent=gammex467_phantom, spacing=[1. * mm, 1. * mm, 1. * mm])
    write_voxelized_geometry(sim, volume_labels, image,
                             paths.output / "gammex467.mhd")

    # run
    sim.run()

    output = itk.GetArrayFromImage(itk.imread(paths.output / "gammex467.mhd"))
    reference = itk.GetArrayFromImage(
        itk.imread(paths.output_ref / "gammex467.mhd"))

    is_ok = np.array_equal(output, reference)

    is_ok = is_ok and filecmp.cmp(paths.output / "gammex467_volumes.json",
                                  paths.output_ref / "gammex467_volumes.json")

    utility.test_ok(is_ok)
