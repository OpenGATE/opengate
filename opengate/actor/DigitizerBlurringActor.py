import opengate as gate
import opengate_core as g4
import numpy as np

sigma_to_fwhm = 2 * np.sqrt(2 * np.log(2))
fwhm_to_sigma = 1.0 / sigma_to_fwhm


class DigitizerBlurringActor(g4.GateDigitizerBlurringActor, gate.ActorBase):
    """
    Digitizer module for blurring an attribute (single value only, not a vector).
    Usually for energy or time.
    """

    type_name = "DigitizerBlurringActor"

    @staticmethod
    def set_default_user_info(user_info):
        gate.ActorBase.set_default_user_info(user_info)
        user_info.attributes = []
        user_info.output = "singles.root"
        user_info.input_digi_collection = "Hits"
        user_info.skip_attributes = []
        user_info.clear_every = 1e5
        user_info.blur_attribute = None
        user_info.blur_method = "Gaussian"
        user_info.blur_fwhm = None
        user_info.blur_sigma = None
        user_info.blur_reference_value = None
        user_info.blur_resolution = None
        user_info.blur_slope = None

    def __init__(self, user_info):
        # check and adjust parameters
        self.set_param(user_info)
        # base classes
        gate.ActorBase.__init__(self, user_info)
        g4.GateDigitizerBlurringActor.__init__(self, user_info.__dict__)
        actions = {"StartSimulationAction", "EndSimulationAction"}
        self.AddActions(actions)

    def set_param(self, user_info):
        am = ["Gaussian", "InverseSquare", "Linear"]
        m = user_info.blur_method
        if m not in am:
            gate.fatal(
                f"Error, the blur_method must be within {am}, while it is {user_info.blur_method}"
            )
        if m == "Gaussian":
            self.set_param_gauss(user_info)
        if m == "InverseSquare":
            self.set_param_inverse_square(user_info)
        if m == "Linear":
            self.set_param_linear(user_info)

    def set_param_gauss(self, user_info):
        if user_info.blur_fwhm is not None and user_info.blur_sigma is not None:
            gate.fatal(
                f"Error, use blur_sigma or blur_fwhm, not both "
                f"(there are: {user_info.blur_sigma} and {user_info.blur_fwhm}"
            )
        if user_info.blur_fwhm is not None:
            user_info.blur_sigma = user_info.blur_fwhm * fwhm_to_sigma
        if user_info.blur_sigma is None:
            gate.fatal(f"Error, use blur_sigma or blur_fwhm")
        user_info.blur_reference_value = -1
        user_info.blur_resolution = -1
        user_info.blur_slope = 0

    def set_param_inverse_square(self, user_info):
        if user_info.blur_reference_value < 0 or user_info.blur_reference_value is None:
            gate.fatal(
                f"Error, use positive blur_reference_value "
                f"(current value =  {user_info.blur_reference_value}"
            )
        if user_info.blur_resolution < 0 or user_info.blur_resolution is None:
            gate.fatal(
                f"Error, use positive blur_resolution "
                f"(current value =  {user_info.blur_resolution}"
            )
        user_info.blur_fwhm = -1
        user_info.blur_sigma = -1
        if user_info.blur_slope is None:
            user_info.blur_slope = 0

    def set_param_linear(self, user_info):
        self.set_param_inverse_square(user_info)
        if user_info.blur_slope is None:
            gate.fatal(
                f"Error, use positive blur_slope "
                f"(current value =  {user_info.blur_slope}"
            )

    def __del__(self):
        pass

    def __str__(self):
        s = f"DigitizerBlurringActor {self.user_info.name}"
        return s

    def StartSimulationAction(self):
        g4.GateDigitizerBlurringActor.StartSimulationAction(self)

    def EndSimulationAction(self):
        g4.GateDigitizerBlurringActor.EndSimulationAction(self)
