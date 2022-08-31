import opengate as gate


class SolidBuilderBase:
    def init_user_info(self, user_info):
        pass

    def Build(self, user_info):
        s = f"You must implement the Build function, and return a G4Solid"
        gate.fatal(s)
