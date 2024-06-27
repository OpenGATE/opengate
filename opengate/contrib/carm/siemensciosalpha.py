import opengate as gate
from opengate.utility import g4_units, get_contrib_path
from scipy.spatial.transform import Rotation
import numpy as np
import spekpy as sp

class Ciosalpha:
    def __init__(self, sim, kvp):
        self.sim = sim
        self.machine_name = "ciosalpha"
        self.volume = self.add_carm_box()
        self.add_xray_tank()
        self.add_collimators()
        self.source = self.add_carm_source(kvp)

    def add_carm_box(self):
        carmbox = self.sim.volume_manager.create_volume("Box", "carmbox")
        carmbox.material = "G4_AIR"
        carmbox.size = [200 * cm, 30 * cm, 200 * cm]
        carmbox.translation = [0 * cm, 0 * cm, 0 * cm]
        carmbox.color = [1, 1, 1, 0.8]

        hole1 = self.sim.volume_manager.create_volume("Box", "hole")
        hole1.size = [191 * cm, 31 * cm, 160 * cm]
        hole1.color = [1, 1, 1, 0.8]
        hole2 = self.sim.volume_manager.create_volume("Box", "hole2")
        hole2.size = [80 * cm, 31 * cm, 31 * cm]
        hole2.color = [1, 1, 1, 0.8]
        hole3 = self.sim.volume_manager.create_volume("Box", "hole3")
        hole3.size = [80 * cm, 31 * cm, 31 * cm]
        hole3.color = [1, 1, 1, 0.8]

        hole1and2 = gate.geometry.volumes.unite_volumes(
            hole1, hole2, translation=[-55.5 * cm, 0 * cm, 95 * cm]
        )

        t_shape = gate.geometry.volumes.unite_volumes(
            hole1and2, hole3, translation=[-55.5 * cm, 0 * cm, -95 * cm]
        )

        carm = gate.geometry.volumes.subtract_volumes(
            carmbox, t_shape, new_name=self.machine_name, translation=[-5 * cm, 0 * cm, -10 * cm]
        )
        self.sim.add_volume(carm)

        return carm

    def add_xray_tank(self):
        xray_tank = self.sim.add_volume("Box", f"{self.machine_name}_xray_tank")
        xray_tank.mother = self.machine_name
        xray_tank.material = "G4_AIR"
        xray_tank.size = [40 * cm, 20 * cm, 30 * cm]
        xray_tank.translation = [0 * cm, 0, 85 * cm]
        xray_tank.color = [1, 1, 1, 0.8]

    def add_carm_source(self, kvp):
        s = sp.Spek(kvp, th=10, physics='kqp')
        s.filter('Al', 3.0).filter('Cu', 0.1)

        energy_bins, weights = s.get_spectrum()

        b = self.sim.add_volume("Box", f"{self.machine_name}_sourcebox")
        b.mother = f"{self.machine_name}_xray_tank"
        b.translation = [0 * cm, 0 * cm, 10 * cm]
        b.size = [1 * cm, 1 * cm, 1 * cm]

        source = self.sim.add_source("GenericSource", f"{self.machine_name}_source")
        source.mother = f"{self.machine_name}_sourcebox"
        source.particle = "gamma"
        source.position.type = "disc"
        source.position.radius = 0 * mm

        source.direction_relative_to_volume = True
        source.direction.type = "iso"
        source.direction.theta = [0 * deg, 10 * deg]
        source.direction.phi = [0 * deg, 360 * deg]

        source.energy.type = "histogram"
        source.energy.histogram_weight = weights
        source.energy.histogram_energy = energy_bins

        return source

    def add_collimators(self):
        xray_tank = self.sim.volume_manager.get_volume(f"{self.machine_name}_xray_tank")
        z_xray_tank = xray_tank.size[2]

        collimator1 = self.sim.add_volume("Box", f"{self.machine_name}_collimator1")
        collimator1.mother = f"{self.machine_name}_xray_tank"
        collimator1.color = red
        collimator1.translation = [75 * mm, 0 * cm, -z_xray_tank / 2 * mm + 1 * mm]
        collimator1.size = [5 * cm, 10 * cm, 1 * mm]

        collimator2 = self.sim.add_volume("Box", f"{self.machine_name}_collimator2")
        collimator2.mother = f"{self.machine_name}_xray_tank"
        collimator2.color = red
        collimator2.translation = [-75 * mm, 0 * cm, -z_xray_tank / 2 * mm + 1 * mm]
        collimator2.size = [5 * cm, 10 * cm, 1 * mm]

        collimator3 = self.sim.add_volume("Box", f"{self.machine_name}_collimator3")
        collimator3.mother = f"{self.machine_name}_xray_tank"
        collimator3.color = red
        collimator3.translation = [0 * cm, 75 * mm, -z_xray_tank / 2 * mm + 3 * mm]
        collimator3.size = [10 * cm, 5 * cm, 1 * mm]

        collimator4 = self.sim.add_volume("Box", f"{self.machine_name}_collimator4")
        collimator4.mother = f"{self.machine_name}_xray_tank"
        collimator4.color = red
        collimator4.translation = [0 * cm, -75 * mm, -z_xray_tank / 2 * mm + 3 * mm]
        collimator4.size = [10 * cm, 5 * cm, 1 * mm]

        killer = self.sim.add_actor("KillActor", f"target_kill")
        killer.mother = [collimator1.name, collimator2.name, collimator3.name, collimator4.name]

    def update_collimation(self, num, num2):
        if not 0 <= num <= 50 or not 0 <= num2 <= 50:
            raise ValueError("Wrong values for collimation")

        num = 50 - num
        num2 = 50 - num2

        xray_tank = self.sim.volume_manager.get_volume(f"{self.machine_name}_xray_tank")
        z_xray_tank = xray_tank.size[2]

        collimator1 = self.sim.volume_manager.get_volume(f"{self.machine_name}_collimator1")
        collimator1.translation = [75 * mm - num, 0 * cm, -z_xray_tank / 2 * mm + 1 * mm]

        collimator2 = self.sim.volume_manager.get_volume(f"{self.machine_name}_collimator2")
        collimator2.translation = [-75 * mm + num, 0 * cm, -z_xray_tank / 2 * mm + 1 * mm]

        collimator3 = self.sim.volume_manager.get_volume(f"{self.machine_name}_collimator3")
        collimator3.translation = [0 * cm, 75 * mm - num2, -z_xray_tank / 2 * mm + 3 * mm]

        collimator4 = self.sim.volume_manager.get_volume(f"{self.machine_name}_collimator4")
        collimator4.translation = [0 * cm, -75 * mm + num2, -z_xray_tank / 2 * mm + 3 * mm]

    @property
    def collimation(self):
        return self._collimation

    @collimation.setter
    def collimation(self, value):
        self._collimation = value
        self.update_collimation(value[0] / mm, value[1] / mm)

    @property
    def rotation(self):
        return self.volume.rotation

    @rotation.setter
    def rotation(self, value):
        self.volume.rotation = value

    @property
    def translation(self):
        return self.volume.translation

    @translation.setter
    def translation(self, value):
        self.volume.translation = value


# useful units
MeV = gate.g4_units.MeV
keV = gate.g4_units.keV
Bq = gate.g4_units.Bq
deg = gate.g4_units.deg
nm = gate.g4_units.nm
mm = gate.g4_units.mm
m = gate.g4_units.m
cm = gate.g4_units.cm

# colors
red = [1, 0.7, 0.7, 0.8]
blue = [0.5, 0.5, 1, 0.8]
green = [0, 1, 0, 1]