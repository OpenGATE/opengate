"""Example: Using electromagnetic fields."""

import opengate as gate
from opengate.geometry import fields

m = gate.g4_units.m
cm = gate.g4_units.cm
mm = gate.g4_units.mm
mrad = gate.g4_units.mrad
tesla = gate.g4_units.tesla
MeV = gate.g4_units.MeV
volt = gate.g4_units.volt

if __name__ == "__main__":
    sim = gate.Simulation()
    sim.visu = True
    sim.visu_type = "qt"
    sim.number_of_threads = 1

    world = sim.world
    world.size = [2 * m, 2 * m, 2 * m]
    world.material = "G4_Galactic"

    box = sim.add_volume("BoxVolume", "box")
    box.size = [50 * cm, 50 * cm, 50 * cm]
    box.material = "G4_Galactic"

    # Uncomment one of the following field definitions to test different field types

    # --- Uniform magnetic field ---
    field = fields.UniformMagneticField(name="B_uniform")
    field.field_vector = [0, 1 * tesla, 0]
    box.add_field(field)

    # # --- Quadrupole magnetic field ---
    # field = fields.QuadrupoleMagneticField(name="B_quad")
    # field.gradient = 10 * tesla / m
    # box.add_field(field)

    # # --- Custom magnetic field ---
    # def B_func(point):
    #     x, y, z, t = point
    #     return [
    #         0.,
    #         (1 + x*z / m**2) * tesla,
    #         0.]
    # field = fields.CustomMagneticField(name="B_custom")
    # field.field_function = B_func
    # box.add_field(field)

    # # --- Uniform electric field ---
    # field = fields.UniformElectricField(name="E_uniform")
    # field.field_vector = [1e8 * volt / m, 0, 0]
    # box.add_field(field)

    # # --- Custom electric field ---
    # def E_func(point):
    #     x, y, z, t = point
    #     return [1e8 * x*z * volt / m, 0, 0]
    # field = fields.CustomElectricField(name="E_custom")
    # field.field_function = E_func
    # box.add_field(field)

    # # --- Uniform electromagnetic field ---
    # field = fields.UniformElectroMagneticField(name="EM_uniform")
    # field.magnetic_field_vector = [0, 0, 1 * tesla]
    # field.electric_field_vector = [1e8 * volt / m, 0, 0]
    # box.add_field(field)

    # # --- Custom electromagnetic field ---
    # def EM_func(point):
    #     x, y, z, t = point
    #     Bx, By, Bz = 0, 1e2 * (1 + x*z / m**2) * tesla, 0
    #     Ex, Ey, Ez = 1e8 * x*z * volt / m, 0, 0
    #     return [Bx, By, Bz, Ex, Ey, Ez]
    # field = fields.CustomElectroMagneticField(name="EM_custom")
    # field.field_function = EM_func
    # box.add_field(field)

    source = sim.add_source("IonPencilBeamSource", "proton_source")
    source.particle = "proton"
    source.n = 100
    source.energy.mono = 10 * MeV
    source.energy.sigma_gauss = 0.1 * source.energy.mono
    source.position.translation = [0, 0, -80 * cm]
    source.position.type = "point"
    source.position.translation = [
        0 * cm,
        0 * cm,
        -100 * cm,
    ]

    source.direction.partPhSp_x = [
    2.3335754 * mm,
    2.3335754 * mrad,
    0.00078728 * mm * mrad,
    0.,
    ]
    source.direction.partPhSp_y = [
        1.96433431 * mm,
        0.00079118 * mrad,
        0.00249161 * mm * mrad,
        0,
    ]

    # Add field visualization and smooth trajectories
    sim.visu_commands += [
        "/tracking/storeTrajectory 2",
        "/vis/scene/add/trajectories smooth",
        "/vis/scene/add/magneticField 10 fullArrow",
        "/vis/scene/add/electricField 10 fullArrow",
    ]

    sim.run()
