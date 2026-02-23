"""Example: Using electromagnetic fields."""

import opengate as gate
from opengate.geometry import fields

g4_m = gate.g4_units.m
g4_cm = gate.g4_units.cm
g4_mm = gate.g4_units.mm
g4_mrad = gate.g4_units.mrad
g4_tesla = gate.g4_units.tesla
g4_MeV = gate.g4_units.MeV
g4_volt = gate.g4_units.volt
g4_eplus = gate.g4_units.eplus

print(
    f"Units: 1 m = {g4_m} mm, 1 tesla = {g4_tesla} tesla, 1 MeV = {g4_MeV} MeV, 1 eplus = {g4_eplus} eplus"
)


def cyclotron_radius(T, B, m, q):
    """
    Calculate the cyclotron radius using Geant4 units.
    Inputs:
        T : kinetic energy (Geant4 units, e.g. MeV)
        B : magnetic field (Geant4 units, e.g. tesla)
        m : mass (Geant4 units, e.g. MeV)
        q : charge (Geant4 units, e.g. eplus)
    Returns:
        radius in meters (Geant4 units)
    """
    E = T + m  # total energy
    p = (E**2 - m**2) ** 0.5
    r_metres = p / (q * B * 0.299792458)
    return r_metres / g4_m


def x_out(r, z, x0):
    """
    Calculate the x position at a given z for a particle in a uniform magnetic field.
    Inputs:
        r : radius of curvature (in mm)
        z : z position (in mm)
    Returns:
        x position (in mm)
    """
    return x0 + (r**2 - (r - z) ** 2) ** 0.5


if __name__ == "__main__":
    sim = gate.Simulation()
    sim.visu = True
    sim.visu_type = "qt"
    sim.number_of_threads = 1

    world = sim.world
    world.size = [2 * g4_m, 2 * g4_m, 2 * g4_m]
    world.material = "G4_Galactic"

    box = sim.add_volume("BoxVolume", "box")
    box.size = [50 * g4_cm, 50 * g4_cm, 50 * g4_cm]
    box.material = "G4_Galactic"

    # Uncomment one of the following field definitions to test different field types

    # --- Uniform magnetic field ---
    By = 5 * g4_tesla
    field = fields.UniformMagneticField(name="B_uniform")
    field.field_vector = [0, By, 0]
    box.add_field(field)

    T = 230 * g4_MeV
    source = sim.add_source("GenericSource", "proton_source")
    source.particle = "proton"
    source.n = 1
    source.energy.type = "mono"
    source.energy.mono = T
    source.position.type = "point"
    source.position.translation = [
        0 * g4_cm,
        0 * g4_cm,
        -100 * g4_cm,
    ]
    source.direction.type = "momentum"
    source.direction.momentum = [0, 0, 1]

    # Add field visualization and smooth trajectories
    sim.visu_commands += [
        "/tracking/storeTrajectory 2",
        "/vis/scene/add/trajectories smooth",
        "/vis/scene/add/magneticField 10 fullArrow",
        "/vis/scene/add/electricField 10 fullArrow",
    ]

    # Add phase space actor
    phsp = sim.add_actor("PhaseSpaceActor", "phsp")
    phsp.attached_to = box.name
    phsp.attributes = [
        "KineticEnergy",
        "PrePosition",
        "PostPosition",
    ]
    phsp.output_filename = "phsp_uniform_B.root"
    phsp.steps_to_store = "exiting"
    phsp.root_output.write_to_disk = True

    sim.run()

    import uproot
    import pandas as pd

    file = uproot.open("phsp_uniform_B.root")
    phsp = file["phsp;1"]
    df = phsp.arrays(library="pd")
    print(df)

    # Compute the real expected deflection
    T = T
    mp = 938.27208943 * g4_MeV
    q = 1 * g4_eplus
    B = By
    r = cyclotron_radius(T, B, mp, q)
    print(f"Expected radius of curvature: {r:.3f} mm")

    xout = x_out(r, 250 * g4_mm, -250 * g4_mm)
    print(f"Expected deflection at 25 cm: {xout:.3f} mm")
