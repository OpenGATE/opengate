import opengate as gate
from opengate.utility import g4_units
import numpy as np
import spekpy as sp

# useful units
MeV = gate.g4_units.MeV
keV = gate.g4_units.keV
Bq = gate.g4_units.Bq
deg = gate.g4_units.deg
nm = gate.g4_units.nm
mm = gate.g4_units.mm
m = gate.g4_units.m
cm = gate.g4_units.cm


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
        carmbox.size = [200 * cm, 30 * cm, 120 * cm]
        carmbox.translation = [0 * cm, 0 * cm, 0 * cm]
        carmbox.color = [1, 1, 1, 0.8]

        hole1 = self.sim.volume_manager.create_volume("Box", "hole")
        hole1.size = [191 * cm, 31 * cm, 80 * cm]
        hole1.color = [1, 1, 1, 0.8]
        hole2 = self.sim.volume_manager.create_volume("Box", "hole2")
        hole2.size = [100 * cm, 31 * cm, 31 * cm]
        hole2.color = [1, 1, 1, 0.8]
        hole3 = self.sim.volume_manager.create_volume("Box", "hole3")
        hole3.size = [100 * cm, 31 * cm, 31 * cm]
        hole3.color = [1, 1, 1, 0.8]

        hole1and2 = gate.geometry.volumes.unite_volumes(
            hole1, hole2, translation=[-55.5 * cm, 0 * cm, 55 * cm]
        )

        t_shape = gate.geometry.volumes.unite_volumes(
            hole1and2, hole3, translation=[-55.5 * cm, 0 * cm, -55 * cm]
        )

        carm = gate.geometry.volumes.subtract_volumes(
            carmbox,
            t_shape,
            new_name=self.machine_name,
            translation=[-5 * cm, 0 * cm, -10 * cm],
        )
        self.sim.add_volume(carm)

        return carm

    def add_xray_tank(self):
        xray_tank = self.sim.add_volume("Box", f"{self.machine_name}_xray_tank")
        xray_tank.mother = self.machine_name
        xray_tank.material = "G4_AIR"
        xray_tank.size = [20 * cm, 20 * cm, 30 * cm]
        xray_tank.translation = [0 * cm, 0, 45 * cm]
        xray_tank.color = [1, 1, 1, 0.8]

    def add_carm_source(self, kvp):
        s = sp.Spek(kvp, th=10, physics="kqp")
        s.filter("Al", 3.0).filter("Cu", 0.1)

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

        collimators = [
            {
                "translation": [75 * mm, 0 * cm, -z_xray_tank / 2 * mm + 1 * mm],
                "size": [5 * cm, 10 * cm, 1 * mm],
            },
            {
                "translation": [-75 * mm, 0 * cm, -z_xray_tank / 2 * mm + 1 * mm],
                "size": [5 * cm, 10 * cm, 1 * mm],
            },
            {
                "translation": [0 * cm, 75 * mm, -z_xray_tank / 2 * mm + 3 * mm],
                "size": [10 * cm, 5 * cm, 1 * mm],
            },
            {
                "translation": [0 * cm, -75 * mm, -z_xray_tank / 2 * mm + 3 * mm],
                "size": [10 * cm, 5 * cm, 1 * mm],
            },
        ]

        for i, colli in enumerate(collimators):
            collimator = self.sim.add_volume(
                "Box", f"{self.machine_name}_collimator{i+1}"
            )
            collimator.mother = f"{self.machine_name}_xray_tank"
            collimator.color = [1, 0.7, 0.7, 0.8]
            collimator.translation = colli["translation"]
            collimator.size = colli["size"]

        killer = self.sim.add_actor("KillActor", f"target_kill")
        killer.mother = [f"{self.machine_name}_collimator{i+1}" for i in range(4)]

    def set_collimation(self, collimation1, collimation2):
        if not 0 <= collimation1 <= 50 or not 0 <= collimation2 <= 50:
            raise ValueError("Collimation values must be between 0 and 50 mm")

        collimation1 = 50 - collimation1
        collimation2 = 50 - collimation2

        xray_tank = self.sim.volume_manager.get_volume(f"{self.machine_name}_xray_tank")
        z_xray_tank = xray_tank.size[2]

        translations = [
            [75 * mm - collimation1, 0 * cm, -z_xray_tank / 2 * mm + 1 * mm],
            [-75 * mm + collimation1, 0 * cm, -z_xray_tank / 2 * mm + 1 * mm],
            [0 * cm, 75 * mm - collimation2, -z_xray_tank / 2 * mm + 3 * mm],
            [0 * cm, -75 * mm + collimation2, -z_xray_tank / 2 * mm + 3 * mm],
        ]

        for i, translation in enumerate(translations):
            collimator = self.sim.volume_manager.get_volume(
                f"{self.machine_name}_collimator{i+1}"
            )
            collimator.translation = translation

    @property
    def collimation(self):
        return self._collimation

    @collimation.setter
    def collimation(self, value):
        self._collimation = value
        self.set_collimation(value[0], value[1])

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
