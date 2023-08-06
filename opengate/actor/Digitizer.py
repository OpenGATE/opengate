class Digitizer:
    """
    Simple helper class to reduce the code size when creating a digitizer.
    It only avoids repeating mother, output and input_digi_collection parameters.
    """

    def __init__(self, sim, volume_name, digit_name):
        # input param
        self.simulation = sim
        self.volume_name = volume_name
        self.name = digit_name
        # store
        self.actors = []

        # start by the hit collection
        self.hc = self.set_hit_collection()

    def set_hit_collection(self):
        hc = self.simulation.add_actor(
            "DigitizerHitsCollectionActor", f"{self.name}_hits"
        )
        hc.mother = self.volume_name
        hc.output = ""
        hc.attributes = [
            "PostPosition",
            "TotalEnergyDeposit",
            "PreStepUniqueVolumeID",
            "PostStepUniqueVolumeID",
            "GlobalTime",
        ]
        self.actors.append(hc)
        return hc

    def add_module(self, module_type, module_name=None):
        index = len(self.actors)
        if module_name is None:
            module_name = f"{self.name}_{index}"
        mod = self.simulation.add_actor(module_type, module_name)
        mod.mother = self.actors[index - 1].mother
        if "input_digi_collection" in mod.__dict__:
            mod.input_digi_collection = self.actors[index - 1].name
        mod.output = ""
        self.actors.append(mod)
        return mod

    def get_last_module(self):
        return self.actors[-1]

    def find_first_module(self, s):
        """
        Find the first module that contains the s string
        """
        for m in self.actors:
            if s in m.name:
                return m
        return None
