import numpy as np

import opengate as gate
import opengate_core as g4


class TemplateSource(gate.SourceBase):
    """
    Source template: to create a new type of source, copy-paste
    this file and adapt to your needs.
    Also declare the source type in the file helpers_source.py
    """

    type_name = "TemplateSource"

    @staticmethod
    def set_default_user_info(user_info):
        gate.SourceBase.set_default_user_info(user_info)
        # initial user info
        user_info.n = 0
        user_info.float_value = None
        user_info.vector_value = None

    def __del__(self):
        pass

    def create_g4_source(self):
        return g4.GateTemplateSource()

    def __init__(self, user_info):
        super().__init__(user_info)

    def initialize(self, run_timing_intervals):
        # Check user_info type
        if self.user_info.float_value is None:
            gate.fatal(
                f"Error for source {self.user_info.name}, float_value must be a float"
            )
        if self.user_info.vector_value is None:
            gate.fatal(
                f"Error for source {self.user_info.name}, vector_value must be a vector"
            )

        # initialize
        gate.SourceBase.initialize(self, run_timing_intervals)
