import opengate as gate
from scipy.spatial.transform import Rotation
import numpy as np
from opengate.utility import LazyModuleLoader

sp = LazyModuleLoader("spekpy")
import pathlib

# useful units
MeV = gate.g4_units.MeV
keV = gate.g4_units.keV
Bq = gate.g4_units.Bq
deg = gate.g4_units.deg
nm = gate.g4_units.nm
mm = gate.g4_units.mm
m = gate.g4_units.m
cm = gate.g4_units.cm

current_path = pathlib.Path(__file__).parent.resolve()


class Ciosalpha:
    def __init__(self, sim, kvp, source_only=False):
        self.sim = sim
        self.machine_name = "ciosalpha"
        self.source_only = source_only
        self.volume = self.add_carm_box()
        self.add_xray_tank()
        self.add_collimators()
        self.source = self.add_carm_source(kvp)

    def add_carm_box(self):
        carmbox = self.sim.volume_manager.create_volume("Box", "carmbox")
        carmbox.material = "G4_AIR"
        carmbox.size = [200 * cm, 10 * cm, 120 * cm]
        carmbox.translation = [0 * cm, 0 * cm, 0 * cm]
        carmbox.color = [1, 1, 1, 0.8]

        hole1 = self.sim.volume_manager.create_volume("Box", "hole")
        hole1.size = [191 * cm, 31 * cm, 80 * cm]
        hole1.color = [1, 1, 1, 0.8]
        hole2 = self.sim.volume_manager.create_volume("Box", "hole2")
        hole2.size = [101 * cm, 31 * cm, 31 * cm]
        hole2.color = [1, 1, 1, 0.8]
        hole3 = self.sim.volume_manager.create_volume("Box", "hole3")
        hole3.size = [90 * cm, 31 * cm, 31 * cm]
        hole3.color = [1, 1, 1, 0.8]

        hole1and2 = gate.geometry.volumes.unite_volumes(
            hole1, hole2, translation=[-50.5 * cm, 0 * cm, 55 * cm]
        )

        subtract_to_carm = gate.geometry.volumes.unite_volumes(
            hole1and2, hole3, translation=[-50.5 * cm, 0 * cm, -55 * cm]
        )

        if self.source_only:
            hole4 = self.sim.volume_manager.create_volume("Box", "hole4")
            hole4.size = [45 * cm, 31 * cm, 31 * cm]
            hole4.color = [1, 1, 1, 0.8]
            hole5 = self.sim.volume_manager.create_volume("Box", "hole5")
            hole5.size = [100 * cm, 31 * cm, 121 * cm]
            hole5.color = [1, 1, 1, 0.8]

            hole4and5 = gate.geometry.volumes.unite_volumes(
                hole4, hole5, translation=[55 * cm, 0 * cm, 45 * cm]
            )

            subtract_to_carm = gate.geometry.volumes.unite_volumes(
                subtract_to_carm, hole4and5, translation=[5 * cm, 0 * cm, -35 * cm]
            )

        carm = gate.geometry.volumes.subtract_volumes(
            carmbox,
            subtract_to_carm,
            new_name=self.machine_name,
            translation=[-5 * cm, 0 * cm, -10 * cm],
        )
        self.sim.add_volume(carm)

        return carm

    def add_xray_tank(self):
        xray_tank = self.sim.add_volume("Box", f"{self.machine_name}_xray_tank")
        xray_tank.mother = self.machine_name
        xray_tank.material = "G4_AIR"
        xray_tank.size = [10 * cm, 10 * cm, 30 * cm]
        xray_tank.translation = [0 * cm, 0, 45 * cm]
        xray_tank.color = [1, 1, 1, 0.8]

    def add_carm_source(self, kvp):
        s = sp.Spek(kvp, th=10, physics="kqp")
        s.filter("Al", 3.0).filter("Cu", 0.1)

        energy_bins, weights = s.get_spectrum()

        sourcebox = self.sim.add_volume("Box", f"{self.machine_name}_sourcebox")
        sourcebox.mother = f"{self.machine_name}_xray_tank"
        sourcebox.translation = [0 * cm, 0 * cm, 10 * cm]
        sourcebox.size = [1 * cm, 1 * cm, 1 * cm]
        sourcebox.rotation = Rotation.from_euler(
            "ZYX", [0, 90, 90], degrees=True
        ).as_matrix()

        source = self.sim.add_source("GenericSource", f"{self.machine_name}_source")
        source.mother = sourcebox.name
        source.particle = "gamma"
        source.position.type = "disc"
        source.position.radius = 0 * mm

        source.direction_relative_to_attached_volume = True
        source.direction.type = "histogram"
        source.direction.histogram_theta_weight = [0, 1]
        source.direction.histogram_theta_angle = [85 * deg, 95 * deg]

        # TODO: Need real values for the anode heel effect
        data = np.load(current_path / "anodeheeleffect.npz")
        source.direction.histogram_phi_weight = data["weight"]
        source.direction.histogram_phi_angle = data["angle"]

        source.energy.type = "histogram"
        source.energy.histogram_weight = weights
        source.energy.histogram_energy = energy_bins

        source.direction.acceptance_angle.volumes = [sourcebox.name]
        source.direction.acceptance_angle.normal_flag = True
        source.direction.acceptance_angle.normal_vector = [1, 0, 0]
        source.direction.acceptance_angle.normal_tolerance = 5 * deg
        source.direction.acceptance_angle.skip_policy = "SkipEvents"

        return source

    def add_collimators(self):
        xray_tank = self.sim.volume_manager.get_volume(f"{self.machine_name}_xray_tank")
        z_xray_tank = xray_tank.size[2]

        collimators = [
            {
                "translation": [37.5 * mm, 0 * cm, -z_xray_tank / 2 * mm + 1 * mm],
                "size": [2.5 * cm, 5 * cm, 1 * mm],
            },
            {
                "translation": [-37.5 * mm, 0 * cm, -z_xray_tank / 2 * mm + 1 * mm],
                "size": [2.5 * cm, 5 * cm, 1 * mm],
            },
            {
                "translation": [0 * cm, 37.5 * mm, -z_xray_tank / 2 * mm + 3 * mm],
                "size": [5 * cm, 2.5 * cm, 1 * mm],
            },
            {
                "translation": [0 * cm, -37.5 * mm, -z_xray_tank / 2 * mm + 3 * mm],
                "size": [5 * cm, 2.5 * cm, 1 * mm],
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
        killer.attached_to = [f"{self.machine_name}_collimator{i+1}" for i in range(4)]

    def set_collimation(self, collimation1, collimation2):
        if not 0 <= collimation1 <= 25 or not 0 <= collimation2 <= 25:
            raise ValueError("Collimation values must be between 0 and 25 mm")

        collimation1 = 25 - collimation1
        collimation2 = 25 - collimation2

        xray_tank = self.sim.volume_manager.get_volume(f"{self.machine_name}_xray_tank")
        z_xray_tank = xray_tank.size[2]

        translations = [
            [37.5 * mm - collimation1, 0 * cm, -z_xray_tank / 2 * mm + 1 * mm],
            [-37.5 * mm + collimation1, 0 * cm, -z_xray_tank / 2 * mm + 1 * mm],
            [0 * cm, 37.5 * mm - collimation2, -z_xray_tank / 2 * mm + 3 * mm],
            [0 * cm, -37.5 * mm + collimation2, -z_xray_tank / 2 * mm + 3 * mm],
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
