import opengate as gate
import opengate_core as g4
import numpy as np


sigma_to_fwhm = 2 * np.sqrt(2 * np.log(2))
fwhm_to_sigma = 1.0 / sigma_to_fwhm


class DigitizerSpatialBlurringActor(
    g4.GateDigitizerSpatialBlurringActor, gate.ActorBase
):
    """
    Digitizer module for blurring a (global) spatial position.
    """

    type_name = "DigitizerSpatialBlurringActor"

    @staticmethod
    def set_default_user_info(user_info):
        gate.ActorBase.set_default_user_info(user_info)
        user_info.attributes = []
        user_info.output = "singles.root"
        user_info.input_digi_collection = "Hits"
        user_info.skip_attributes = []
        user_info.clear_every = 1e5
        user_info.blur_attribute = None
        user_info.blur_fwhm = None
        user_info.blur_sigma = None
        user_info.keep_in_solid_limits = True

    def __init__(self, user_info):
        # check and adjust parameters
        self.set_param(user_info)
        # base classes
        gate.ActorBase.__init__(self, user_info)
        if not hasattr(user_info.blur_sigma, "__len__"):
            user_info.blur_sigma = [user_info.blur_sigma] * 3
        g4.GateDigitizerSpatialBlurringActor.__init__(self, user_info.__dict__)
        actions = {"StartSimulationAction", "EndSimulationAction"}
        self.AddActions(actions)

    def set_param(self, user_info):
        if user_info.blur_fwhm is not None and user_info.blur_sigma is not None:
            gate.fatal(
                f"Error, use blur_sigma or blur_fwhm, not both "
                f"(there are: {user_info.blur_sigma} and {user_info.blur_fwhm}"
            )
        if user_info.blur_fwhm is not None:
            user_info.blur_sigma = np.array(user_info.blur_fwhm) * fwhm_to_sigma
        if user_info.blur_sigma is None:
            gate.fatal(f"Error, use blur_sigma or blur_fwhm")

    def __del__(self):
        pass

    def __str__(self):
        s = f"DigitizerSpatialBlurringActor {self.user_info.name}"
        return s

    def StartSimulationAction(self):
        g4.GateDigitizerSpatialBlurringActor.StartSimulationAction(self)

    def EndSimulationAction(self):
        g4.GateDigitizerSpatialBlurringActor.EndSimulationAction(self)
