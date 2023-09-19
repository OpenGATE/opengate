from ..userelement import UserElement
from ..definitions import __world_name__
from ..helpers import g4_units
from ..exception import fatal, warning


def get_simplified_digitizer_channels_Tc99m(spect_name, scatter_flag):
    keV = g4_units("keV")
    # Tc99m
    channels = [
        {"name": f"scatter_{spect_name}", "min": 114 * keV, "max": 126 * keV},
        {"name": f"peak140_{spect_name}", "min": 126 * keV, "max": 154 * keV},
    ]
    if not scatter_flag:
        channels.pop(0)
    return channels


def get_simplified_digitizer_channels_Lu177(spect_name, scatter_flag):
    # Lu177, Ljungberg2016
    keV = g4_units("keV")
    channels = [
        {"name": f"scatter1_{spect_name}", "min": 96 * keV, "max": 104 * keV},
        {"name": f"peak113_{spect_name}", "min": 104 * keV, "max": 121.48 * keV},
        {"name": f"scatter2_{spect_name}", "min": 122.48 * keV, "max": 133.12 * keV},
        {"name": f"scatter3_{spect_name}", "min": 176.46 * keV, "max": 191.36 * keV},
        {"name": f"peak208_{spect_name}", "min": 192.36 * keV, "max": 223.6 * keV},
    ]
    if not scatter_flag:
        channels.pop(0)
        channels.pop(1)
        channels.pop(1)
    return channels


def get_simplified_digitizer_channels_In111(spect_name, scatter_flag):
    # In111
    keV = g4_units("keV")
    channels = [
        {"name": f"scatter1_{spect_name}", "min": 150 * keV, "max": 156 * keV},
        {"name": f"peak171_{spect_name}", "min": 156 * keV, "max": 186 * keV},
        {"name": f"scatter2_{spect_name}", "min": 186 * keV, "max": 192 * keV},
        {"name": f"scatter3_{spect_name}", "min": 218 * keV, "max": 224 * keV},
        {"name": f"peak245_{spect_name}", "min": 224 * keV, "max": 272 * keV},
    ]
    if not scatter_flag:
        channels.pop(0)
        channels.pop(1)
        channels.pop(1)
    return channels


def get_simplified_digitizer_channels_I131(spect_name, scatter_flag):
    # I131
    keV = g4_units("keV")
    channels = [
        {"name": f"scatter1_{spect_name}", "min": 314 * keV, "max": 336 * keV},
        {"name": f"peak364_{spect_name}", "min": 336 * keV, "max": 392 * keV},
        {"name": f"scatter2_{spect_name}", "min": 392 * keV, "max": 414 * keV},
        {"name": f"scatter3_{spect_name}", "min": 414 * keV, "max": 556 * keV},
        {"name": f"scatter4_{spect_name}", "min": 556 * keV, "max": 595 * keV},
        {"name": f"peak637_{spect_name}", "min": 595 * keV, "max": 679 * keV},
    ]
    if not scatter_flag:
        channels.pop(0)
        channels.pop(1)
        channels.pop(1)
        channels.pop(1)
    return channels


def get_simplified_digitizer_channels_rad(spect_name, rad, scatter_flag):
    available_rad = {
        "Tc99m": get_simplified_digitizer_channels_Tc99m,
        "Lu177": get_simplified_digitizer_channels_Lu177,
        "In111": get_simplified_digitizer_channels_In111,
        "I131": get_simplified_digitizer_channels_I131,
    }

    if rad not in available_rad:
        fatal(
            f"Error, the radionuclide {rad} is not known, list of available is: {available_rad}"
        )

    return available_rad[rad](spect_name, scatter_flag)


class ActorBase(UserElement):
    """
    Store user information about an actor
    """

    element_type = "Actor"

    @staticmethod
    def set_default_user_info(user_info):
        UserElement.set_default_user_info(user_info)
        # user properties shared for all actors
        user_info.mother = __world_name__
        user_info.filters = []
        user_info.priority = 100

    def __init__(self, user_info):
        # type_name MUST be defined in class that inherit from ActorBase
        super().__init__(user_info)
        # list of filters for this actor
        self.filters_list = []
        # store the output
        # FIXME: check if this is needed. Does not seem to be used anywhere
        self.actor_output = None
        # engines
        self.simulation_engine_wr = None
        self.volume_engine = None
        # sim
        self.simulation = None

    def close(self):
        if self.verbose_close:
            warning(
                f"Closing ActorBase {self.user_info.type_name} {self.user_info.name}"
            )
        self.volume_engine = None
        self.simulation_engine_wr = None
        self.simulation = None
        for v in self.__dict__:
            if "g4_" in v:
                self.__dict__[v] = None
        for filter in self.filters_list:
            filter.close()

    def __getstate__(self):
        """
        This is important : to get actor's outputs from a simulation run in a separate process,
        the class must be serializable (pickle).
        The engines (volume, actor, etc.) and G4 objects are also removed if exists.
        """
        if self.verbose_getstate:
            warning(
                f"Getstate ActorBase {self.user_info.type_name} {self.user_info.name}"
            )
        # do not pickle engines and g4 objects
        for v in self.__dict__:
            if "_engine" in v or "g4_" in v:
                self.__dict__[v] = None
        try:
            self.__dict__["simulation"] = None
        except KeyError:
            print("No simulation to be removed while pickling Actor")
        # we remove the filter that trigger a pickle error
        # (to be modified)
        self.filters_list = []
        return self.__dict__

    def initialize(self, simulation_engine_wr=None):
        self.simulation_engine_wr = simulation_engine_wr
        self.volume_engine = self.simulation_engine_wr().volume_engine
        # 'l' must be self to avoid being deleted
        # self.filters_list = []
        # for f in self.user_info.filters:
        #     e = new_element(f, self.simulation)
        #     e.Initialize(f.__dict__)
        #     self.filters_list.append(e)
        # # this is a copy to cpp ('append' cannot be used because fFilters is a std::vector)
        # self.fFilters = self.filters_list

    def __str__(self):
        s = f"str ActorBase {self.user_info.name} of type {self.user_info.type_name}"
        return s
